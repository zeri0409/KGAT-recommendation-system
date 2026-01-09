#!/usr/bin/env python
"""检查模型文件的键名"""
import torch
from collections import OrderedDict

model_path = "trained_model/model_epoch44.pth"
checkpoint = torch.load(model_path, map_location='cpu')

print("=" * 60)
print("模型文件检查")
print("=" * 60)
print(f"\nEpoch: {checkpoint.get('epoch', '未知')}")
print(f"\n模型状态字典的键名 ({len(checkpoint['model_state_dict'])} 个):")
print("-" * 60)

for key in sorted(checkpoint['model_state_dict'].keys()):
    shape = checkpoint['model_state_dict'][key].shape
    print(f"  {key:50s} {str(shape)}")

print("\n" + "=" * 60)
print("期望的键名（当前代码）:")
print("-" * 60)
expected_keys = [
    "W_R",
    "relation_embed.weight",
    "entity_user_embed.weight",
    "aggregator_layers.0.W1.weight",
    "aggregator_layers.0.W1.bias",
    "aggregator_layers.0.W2.weight",
    "aggregator_layers.0.W2.bias",
]

for key in expected_keys:
    exists = key in checkpoint['model_state_dict']
    status = "✓" if exists else "✗"
    print(f"  {status} {key}")

print("\n" + "=" * 60)

