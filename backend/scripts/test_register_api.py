#!/usr/bin/env python
"""测试注册接口"""
import requests
import json

# 测试注册
url = "http://127.0.0.1:8000/api/auth/register"

# 测试1: 新用户注册
print("=" * 60)
print("测试1: 注册新用户")
print("=" * 60)
try:
    response = requests.post(url, json={
        "username": "testuser999",
        "password": "test123456"
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

print("\n")

# 测试2: 重复注册（应该失败）
print("=" * 60)
print("测试2: 重复注册（应该失败）")
print("=" * 60)
try:
    response = requests.post(url, json={
        "username": "testuser999",
        "password": "test123456"
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except requests.exceptions.HTTPError as e:
    print(f"HTTP错误: {e.response.status_code}")
    print(f"响应: {json.dumps(e.response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

