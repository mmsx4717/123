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
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # 注意检查官方文档确认最新 URL

# 超时时间和重试次数（可通过环境变量配置）
DEEPSEEK_TIMEOUT = float(os.getenv('DEEPSEEK_TIMEOUT', '120'))  # 默认 120 秒
DEEPSEEK_MAX_RETRIES = int(os.getenv('DEEPSEEK_MAX_RETRIES', '2'))  # 默认最多重试 2 次


def call_deepseek(messages):
    """
    调用 DeepSeek 的封装，带超时配置和简单重试。
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("错误：未在 .env 文件中设置 DEEPSEEK_API_KEY")

    payload = {
        "model": "deepseek-chat",  # 根据 DeepSeek 文档确认模型名称
        "messages": messages,
        "stream": False,  # 先用非流式
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(1, DEEPSEEK_MAX_RETRIES + 2):  # 首次请求 + 若干次重试
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=DEEPSEEK_TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                ai_message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                if not ai_message:
                    raise ValueError("从 DeepSeek API 返回的数据中没有找到 message.content")
                return ai_message

            # 非 200，记录错误信息，视为一次失败
            last_error = f"状态码 {response.status_code}, 响应: {response.text}"
            print(f"[DeepSeek 调用失败][第 {attempt} 次] {last_error}")

        except requests.exceptions.Timeout as e:
            last_error = f"请求 DeepSeek API 超时（第 {attempt} 次），超时时间 {DEEPSEEK_TIMEOUT} 秒: {e}"
            print(last_error)
        except requests.exceptions.RequestException as e:
            last_error = f"请求 DeepSeek API 发生网络相关异常（第 {attempt} 次）: {e}"
            print(last_error)
        except Exception as e:
            last_error = f"处理 DeepSeek 响应时发生未知错误（第 {attempt} 次）: {e}"
            print(last_error)

    # 所有尝试均失败
    raise RuntimeError(last_error or "调用 DeepSeek API 失败，原因未知")

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

    try:
        # 调用 DeepSeek（带超时和重试）
        ai_message = call_deepseek(user_messages)

        # 正常拿到回复
        return jsonify({
            "reply": ai_message,
            "meta": {
                "timeout": DEEPSEEK_TIMEOUT,
                "max_retries": DEEPSEEK_MAX_RETRIES,
            }
        }), 200

    except RuntimeError as e:
        # 所有重试都失败
        print(f"调用 DeepSeek 失败（已重试）: {e}")
        return jsonify({
            "error": "调用 DeepSeek 失败，请稍后重试",
            "details": str(e)
        }), 502  # Bad Gateway，更贴近“上游服务失败”
    except Exception as e:
        # 其他意外错误
        print(f"处理请求时发生未知错误: {e}")
        return jsonify({"error": "内部服务器错误"}), 500


if __name__ == '__main__':
    # 本地开发时运行
    # 注意：生产环境推荐使用 Gunicorn, uWSGI 等 WSGI 服务器
    app.run(host='127.0.0.1', port=5000, debug=True)