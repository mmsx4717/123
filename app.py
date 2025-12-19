import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_APP_SECRET_KEY') # 设置 Flask 密钥

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions" # 注意检查官方文档确认最新 URL

# 检查 API Key 是否已配置
if not DEEPSEEK_API_KEY:
    raise ValueError("错误：未在 .env 文件中设置 DEEPSEEK_API_KEY")

@app.route('/')
def index():
    return "Hello, this is the DeepSeek WeChat Bot Backend!"

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    处理来自小程序的聊天请求。
    预期的 JSON 请求体格式：
    {
      "messages": [
        {"role": "system", "content": "你是..."}, # 可选
        {"role": "user", "content": "你好"}
      ]
    }
    """
    data = request.get_json()
    
    # 基本校验
    if not data or 'messages' not in data or not isinstance(data['messages'], list):
         return jsonify({"error": "请求体格式错误，缺少 'messages' 列表"}), 400

    user_messages = data['messages']

    # 准备发送给 DeepSeek API 的数据
    payload = {
        "model": "deepseek-chat", # 根据 DeepSeek 文档确认模型名称
        "messages": user_messages,
        "stream": False # 我们先处理非流式响应
        # 可以根据需要添加 temperature, max_tokens 等参数
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # 调用 DeepSeek API
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        
        # 检查 DeepSeek API 响应状态码
        if response.status_code == 200:
            response_data = response.json()
            
            # 提取 AI 的回复
            ai_message = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if ai_message:
                # 返回 AI 回复给小程序
                return jsonify({"reply": ai_message}), 200
            else:
                return jsonify({"error": "未能从 DeepSeek API 获取有效回复内容"}), 500
        
        else:
            # DeepSeek API 返回了错误
            error_info = response.text
            print(f"DeepSeek API 错误 ({response.status_code}): {error_info}") # 服务端日志
            return jsonify({
                "error": f"调用 DeepSeek API 失败",
                "details": error_info # 可以选择性返回详细信息给前端
            }), response.status_code

    except requests.exceptions.Timeout:
        return jsonify({"error": "请求 DeepSeek API 超时"}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        # 网络或其他请求相关错误
        print(f"请求 DeepSeek API 时发生异常: {e}")
        return jsonify({"error": "内部服务器错误，无法连接到 DeepSeek API"}), 500
    except Exception as e:
        # 其他意外错误
        print(f"处理请求时发生未知错误: {e}")
        return jsonify({"error": "内部服务器错误"}), 500


if __name__ == '__main__':
    # 本地开发时运行
    # 注意：生产环境推荐使用 Gunicorn, uWSGI 等 WSGI 服务器
    app.run(host='127.0.0.1', port=5000, debug=True)