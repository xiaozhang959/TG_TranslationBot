# 项目介绍
## 这是一个基于 deeplx 翻译 API 并且使用了 python-telegram-bot 的简单的 Telegram 翻译机器人。

这个机器人可以帮助用户在 Telegram 中实现中文和英文之间的翻译，支持多种交互方式，包括：
- 指令模式：/ts <text>
- 回复模式：回复某条消息，输入 ts、translate、翻译（不需要加 /），支持设置定时删除译文
- 自动翻译模式：/auto 开启/关闭自动翻译功能 ，支持设置定时删除译文 
- 获取用户id和群组id功能：/get_user_id 和 /get_group_id

# 功能

- **文本翻译**：用户可以通过命令 `/translate <text>` 或 `/ts <text>` 翻译指定文本。
- **回复翻译**：用户可以对某条消息进行回复，并在输入框输入 `ts`、`translate`、`翻译`（不需要加 `/`），即可实现翻译指定的消息。
- **自动翻译模式**：通过命令 `/auto` 可以开启或关闭自动翻译所有对话内容。
- **获取用户和群组 ID**：通过命令 `/get_user_id` 和 `/get_group_id` 获取当前用户或群组的 ID。
- **欢迎信息**：通过命令 `/start` 获取机器人的使用说明和功能介绍。

# 部署与使用

1. **环境配置**：

   1.1 本地部署
       - 安装依赖：确保你的 Python 环境中安装了 `python-telegram-bot` 和 `requests` 库。
       - 设置环境变量：
           - `DEEPL_API_URLS`: 你的 deeplx API URL 列表，以逗号分隔。
           - `ALLOWED_CHAT_IDS`: 允许使用机器人的群聊 ID 列表，以逗号分隔。
           - `ALLOWED_USER_IDS`: 允许使用机器人的用户 ID 列表，以逗号分隔。
           - `BOT_TOKEN`: 你的 Telegram 机器人令牌。
           - `DELETE_TIME`: 自动删除翻译消息的时间（秒）。

   1.2 docker部署
      下载项目，然后`cd TG_TranslationBot`, 然后`docker build -t your_tg_bot_name`即可打包成功，后面就`ducker run ....` 。

2. **运行机器人**：
    - 在终端中运行 `python main.py` 启动机器人。

3. **使用机器人**：
    - 在 Telegram 中与机器人对话，使用上述命令进行交互。

# 关于

- **翻译服务**：本机器人的翻译服务基于 deeplx，感谢始皇以及各位大佬提供的 deeplx API。
- **联系信息**：如有问题或需要帮助，请联系 Telegram 用户 [ng0668](https://t.me/ng0668)。
- **注意事项**：本机器人需要自行搭建或与作者申请才能使用，如有需要请说明来意并附带自己的用户 ID 或者群组 ID。

