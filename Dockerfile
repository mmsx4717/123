FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# TCB 会注入 PORT 环境变量，应用需要监听 $PORT
EXPOSE $PORT

# 启动命令，使用 gunicorn 作为生产 WSGI 服务器
# -b 0.0.0.0:$PORT 绑定到所有接口和 TCB 提供的端口
# app:app 指的是 app.py 文件中的 Flask 实例
# 使用 ${PORT:-5000} 语法：如果 $PORT 为空或未设置，则使用默认值 5000
CMD gunicorn -w 1 -b 0.0.0.0:${PORT:-5000} app:app