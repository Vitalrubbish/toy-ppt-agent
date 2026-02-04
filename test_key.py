# 测试 OpenAI api 是否有效

import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 加载 .env 文件
print("正在加载环境变量...")
load_success = load_dotenv()
if load_success:
    print(".env 文件加载成功")
else:
    print(".env 文件加载失败")
    exit(1)
    

# 2. 获取 Key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("未找到 OPENAI_API_KEY，请检查 .env 文件内容或格式。")
    exit(1)
else:
    masked_key = f"{api_key[:6]}...{api_key[-4:]}"
    print(f"读取到 OPENAI_API_KEY: {masked_key}")

# 3. 尝试调用 API
print("\n正在尝试连接 OpenAI API...")

try:
    client = OpenAI(api_key=api_key)
    
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        print(f"ℹ使用 OPENAI_BASE_URL: {base_url}")
        client.base_url = base_url

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello, simply reply with 'API is working!'"}
        ],
        max_tokens=20
    )
    
    result = response.choices[0].message.content
    print(f"API 连接成功! 模型回复: {result}")

except Exception as e:
    print(f"API 调用失败: {e}")
    print("请检查你的 Key 余额、网络连接（是否需要代理）或 Base URL 配置。")
