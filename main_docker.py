import json
import logging
import os
from venv import logger

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# 不使用docker在开发环境下记得 终端执行 pip install "python-telegram-bot[job-queue]"

# 设置主日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # 这是你的主应用日志级别
)

# 获取 httpx 的日志记录器并设置日志级别
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)  # 将 httpx 的日志级别设置为 WARNING 或更高
# 获取 apscheduler.executors.default 的日志记录器并设置日志级别
apscheduler_logger = logging.getLogger("apscheduler.executors.default")
apscheduler_logger.setLevel(logging.WARNING)  # 将日志级别设置为 WARNING 或更高

# 从环境变量中读取配置
DEEPL_API_URLS = os.environ.get("DEEPL_API_URLS", "").split(",")
ALLOWED_CHAT_IDS = list(map(int, os.environ.get("ALLOWED_CHAT_IDS", "").split(",")))
ALLOWED_USER_IDS = list(map(int, os.environ.get("ALLOWED_USER_IDS", "").split(",")))
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# 将 DELETE_TIME 转换为整数
DELETE_TIME = int(os.environ.get("DELETE_TIME", 60))

# 轮询计数器
current_api_index = 0


# 定时删除消息函数
async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id, message_id = context.job.data  # 使用 job.data 而不是 context
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted message {message_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} in chat {chat_id}: {e}")


# 翻译函数
def translate_text(text):
    global current_api_index
    target_lang = "EN" if any(u'\u4e00' <= char <= u'\u9fff' for char in text) else "ZH"
    payload = json.dumps({
        "text": text,
        "source_lang": "auto",
        "target_lang": target_lang
    })
    headers = {
        'Content-Type': 'application/json'
    }

    # 轮询API端点
    api_url = DEEPL_API_URLS[current_api_index]
    current_api_index = (current_api_index + 1) % len(DEEPL_API_URLS)

    logger.info(f"Translating text: {text} using API: {api_url}")

    try:
        response = requests.post(api_url, headers=headers, data=payload)
        response.raise_for_status()
        logger.info(f"Translation response: {response.text}")
        return response.json().get('data', '')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during translation: {e}")
        return "Translation failed."


# 存储多个用户ID和对应的最后一句话及其消息对象
user_last_messages = {}


# 处理翻译命令
async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id

    logger.info(f"Received translate command from user {user_id} in chat {chat_id}")

    # 检查是否在允许的聊天中
    if chat_id in ALLOWED_CHAT_IDS or user_id in ALLOWED_USER_IDS:
        text_to_translate = ' '.join(context.args)  # 获取命令后面的参数
        last_message_obj = None  # 初始化last_message_obj
        if not text_to_translate:
            last_message_info = user_last_messages.get(user_id)
            if last_message_info:
                last_message = last_message_info[0]
                last_message_obj = last_message_info[1]
                text_to_translate = last_message

        if text_to_translate:
            translated_text = translate_text(text_to_translate)
            if last_message_obj:
                await last_message_obj.reply_text(translated_text, quote=True)
                await message.delete()
            else:
                await message.reply_text(translated_text)


# 处理消息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id

    logger.info(f"Handling message from user {user_id} in chat {chat_id}")

    if chat_id in ALLOWED_CHAT_IDS or user_id in ALLOWED_USER_IDS:
        if message and message.text:

            # 如果是回复某条消息并且说翻译或者ts指令，那么就翻译要回复的消息的内容
            if (message.reply_to_message and
                    (message.text.strip() == "翻译" or message.text.strip() == "ts"
                     or message.text.strip() == "translate")):
                text_to_translate = message.reply_to_message.text if message.reply_to_message.text is not None else \
                    message.reply_to_message.caption
                if text_to_translate:
                    translated_text = translate_text(text_to_translate)
                    sent_message = await message.reply_to_message.reply_text(
                        f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）"
                    )
                    # Schedule message deletion
                    context.job_queue.run_once(delete_message, DELETE_TIME, data=(chat_id, sent_message.message_id))
                    await message.delete()
                    return
                else:
                    return  # 如果没有任何内容需要翻译，直接返回

            if (not message.text.startswith('/')
                    and message.text.strip() != "翻译"
                    and message.text.strip() != "ts"
                    and message.text.strip() != f"@{context.bot.username}"):
                user_last_messages[user_id] = (message.text, message)

            if context.user_data.get('all_translate', False):
                translated_text = translate_text(message.text)
                sent_message = await message.reply_text(
                    f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）"
                )
                # Schedule message deletion
                context.job_queue.run_once(delete_message, DELETE_TIME, data=(chat_id, sent_message.message_id))

            if message.entities:
                for entity in message.entities:
                    if entity.type == 'mention' and message.text[
                                                    entity.offset:entity.offset + entity.length] == f"@{context.bot.username}":
                        text_to_translate = message.text.replace(f"@{context.bot.username}", "").strip()
                        last_message_obj = None  # 初始化last_message_obj
                        if text_to_translate:
                            translated_text = translate_text(text_to_translate)
                            await message.reply_text(translated_text)

                            return
                        else:
                            last_message_info = user_last_messages.get(user_id)
                            if last_message_info:
                                last_message, last_message_obj = last_message_info
                                text_to_translate = last_message

                            if text_to_translate:
                                translated_text = translate_text(text_to_translate)
                                if last_message_obj:
                                    await last_message_obj.reply_text(translated_text, quote=True)
                                    await message.delete()
                                else:
                                    sent_message = await message.reply_text(
                                        f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）"
                                    )
                                    context.job_queue.run_once(delete_message, DELETE_TIME,
                                                               data=(chat_id, sent_message.message_id))

            if message.text and (message.text.startswith("翻译") or message.text.startswith("ts")):
                text_to_translate = message.text[2:].strip()
                last_message_obj = None
                if text_to_translate:
                    translated_text = translate_text(text_to_translate)
                    await message.reply_text(translated_text)
                    # Schedule message deletion，输入翻译 xxxxx的时候不应该删除译文，因为有明确需求需要翻译
                    return
                else:
                    last_message_info = user_last_messages.get(user_id)
                    if last_message_info:
                        msg1, last_message_obj = last_message_info
                        last_message = last_message_obj.caption if last_message_obj.caption is not None else \
                            last_message_obj.text

                        text_to_translate = last_message

                    if text_to_translate:
                        translated_text = translate_text(text_to_translate)
                        if last_message_obj:
                            sent_message = await last_message_obj.reply_text(
                                f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）",
                                quote=True
                            )
                            await message.delete()
                        else:
                            sent_message = await message.reply_text(
                                f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）"
                            )
                        # 删除消息
                        context.job_queue.run_once(delete_message, DELETE_TIME, data=(chat_id, sent_message.message_id))

        if message.document:
            caption = message.caption
            if caption:

                caption_parts = caption.split()
                if caption_parts:
                    if caption_parts[0] == '/translate' or caption_parts[0] == '/ts' or caption_parts[0] == '翻译':
                        caption = ' '.join(caption_parts[1:])
                    else:
                        caption = caption
                    # 如果开启了自动翻译：
                    if context.user_data.get('all_translate', False):
                        translated_text = translate_text(caption)
                        sent_message = await message.reply_text(
                            f"{translated_text}\n\n（此消息将于{DELETE_TIME}秒后自动删除/This message will be deleted after {DELETE_TIME} seconds.）"
                        )
                        # Schedule message deletion
                        context.job_queue.run_once(delete_message, DELETE_TIME, data=(chat_id, sent_message.message_id))

                if caption_parts and (
                        caption_parts[0] == '/translate' or caption_parts[0] == '/ts' or caption_parts[0] == '翻译'):
                    caption = ' '.join(caption_parts[1:])
                    # 需要执行翻译命令
                    if caption:
                        translated_text = translate_text(caption)
                        await message.reply_text(translated_text)
                else:
                    # 不需要执行翻译，记录最后一条消息
                    user_last_messages[user_id] = (message.text, message)


# 处理 /allTranslate 命令
async def all_translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id

    logger.info(f"Received allTranslate command from user {user_id} in chat {chat_id}")

    if chat_id in ALLOWED_CHAT_IDS or user_id in ALLOWED_USER_IDS:
        context.user_data['all_translate'] = not context.user_data.get('all_translate', False)
        status = "开启" if context.user_data['all_translate'] else "关闭"
        await message.reply_text(f"已{status}默认翻译所有对话内容")


# 新增获取用户ID的命令处理函数
async def get_user_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"你的用户ID是: {user_id}")


# 新增获取群组ID的命令处理函数
async def get_group_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id < 0:  # 群组的 chat_id 通常是负数，而私人聊天是正数
        await update.message.reply_text(f"这个群组的ID是: {chat_id}")
    else:
        await update.message.reply_text("这个命令只能在群组中使用。")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "欢迎使用我的翻译机器人！\n\n"
        "这个机器人可以帮助你进行中文和英文之间的翻译。\n"
        "你可以使用以下命令：\n"
        "/translate <text> - Translate the specified text\n"
        "/ts <text> - Translate the specified text\n"
        "翻译 <文本> - 翻译指定文本\n"
        "/get_user_id - 获取你的用户ID\n"
        "/get_group_id - 获取当前群组ID\n"
        "/auto - 切换自动翻译模式\n\n"
        "当然你也可以对某条消息进行回复，并在输入框输入ts、translate、翻译（不需要加/）回车，\n"
        "  即可实现翻译指定的消息（需要注意此种方式设定了一定时间后会自动删除译文，如不希望删除译文请使用 [/ts  /translate  翻译 ] xxxx 的形式发送）。\n\n"
        "本机器人的翻译服务基于deeplx，在此感谢始皇以及各位大佬的的deeplx api。\n\n"
        "请注意本机器人需要自行搭建或与我申请才能使用，如有需要请说明来意并附带自己用户id或者群组id \n\n"
        "如果你有任何问题或需要帮助，请随时联系我！\n https://t.me/ng0668"
    )
    await update.message.reply_text(welcome_message)


async def post_init(application):
    # 在这里执行任何需要在初始化后运行的异步逻辑
    await application.job_queue.start()


# 启动Bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    logger.info("Starting bot")

    application.add_handler(CommandHandler("get_user_id", get_user_id_command))
    application.add_handler(CommandHandler("get_group_id", get_group_id_command))
    application.add_handler(CommandHandler("ts", translate_command))
    application.add_handler(CommandHandler("translate", translate_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("auto", all_translate_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION, handle_message))

    application.run_polling()


if __name__ == '__main__':
    main()
