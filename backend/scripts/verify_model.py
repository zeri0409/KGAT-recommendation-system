#!/usr/bin/env python
"""验证模型文件"""
import torch
from pathlib import Path

model_path = Path("trained_model/model_epoch44.pth")

if not model_path.exists():
    print(f"❌ 模型文件不存在: {model_path}")
    exit(1)

print(f"✅ 找到模型文件: {model_path}")
print(f"   文件大小: {model_path.stat().st_size / (1024*1024):.2f} MB")

try:
    checkpoint = torch.load(str(model_path), map_location='cpu')
    print("\n✅ 模型文件可以正常加载")
    print(f"   包含的键: {list(checkpoint.keys())}")
    if 'epoch' in checkpoint:
        print(f"   Epoch: {checkpoint['epoch']}")
    if 'model_state_dict' in checkpoint:
        print(f"   模型状态字典包含 {len(checkpoint['model_state_dict'])} 个参数组")
except Exception as e:
    print(f"\n❌ 加载模型文件失败: {e}")
    exit(1)

print("\n✅ 模型文件验证通过！")

