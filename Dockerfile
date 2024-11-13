# 使用官方 Python 镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 将当前目录的内容复制到工作目录中
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

ENV DEEPL_API_URLS=<your_deepl_api_urls>
ENV ALLOWED_CHAT_IDS=<your_allowed_chat_ids>
ENV ALLOWED_USER_IDS=<your_allowed_user_ids>
ENV BOT_TOKEN=<your_bot_token>
ENV DEEPL_API_KEY=<your_deepl_api_key>


# 运行应用程序
CMD ["python", "main.py"]
