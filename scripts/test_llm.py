#!/usr/bin/env python3
"""快速测试 MiniMax API Key 是否可用"""

import json
import sys

try:
    from openai import OpenAI
except ImportError:
    print("需要安装 openai: pip install openai")
    sys.exit(1)

# 读取配置
config_path = "config.json"
with open(config_path) as f:
    cfg = json.load(f)["llm"]

print(f"Provider: {cfg['provider']}")
print(f"Model: {cfg['model']}")
print(f"Base URL: {cfg['base_url']}")

# 创建客户端
client = OpenAI(
    api_key=cfg["api_key"],
    base_url=cfg["base_url"]
)

# 发送测试请求
print("\n正在测试 API...")
try:
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "user", "content": "请用中文回复：你好！API 连接成功！"}],
        max_tokens=100,
        temperature=0.7
    )
    content = resp.choices[0].message.content
    print(f"\n成功! 响应:\n{content}")
    
    # 打印 usage 信息
    if resp.usage:
        print(f"\nToken 使用: prompt={resp.usage.prompt_tokens}, completion={resp.usage.completion_tokens}, total={resp.usage.total_tokens}")
    
    print("\n✓ MiniMax API Key 测试通过!")
except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    sys.exit(1)
