#!/usr/bin/env python
"""
检查KGAT模型训练状态
"""
import os
import glob
from pathlib import Path

def check_training_status():
    """检查训练状态"""
    model_dir = Path("trained_model/KGAT/amazon-book/entitydim64_relationdim64_bi-interaction_64-32-16_lr0.0001_pretrain1")
    
    print("=" * 60)
    print("KGAT模型训练状态检查")
    print("=" * 60)
    
    # 检查目录是否存在
    if not model_dir.exists():
        print(f"❌ 训练目录不存在: {model_dir}")
        print("   训练可能还在初始化阶段（加载数据等）")
        print("   请稍候再检查...")
        return
    
    print(f"✅ 训练目录存在: {model_dir}")
    
    # 检查日志文件
    log_files = list(model_dir.glob("log*.txt"))
    if log_files:
        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
        print(f"\n📋 最新日志文件: {latest_log.name}")
        print(f"   修改时间: {latest_log.stat().st_mtime}")
        
        # 读取最后几行
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print(f"\n   最后5行日志:")
                    for line in lines[-5:]:
                        print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"   无法读取日志: {e}")
    else:
        print("\n⚠️  未找到日志文件")
    
    # 检查模型文件
    model_files = list(model_dir.glob("model_epoch*.pth"))
    if model_files:
        print(f"\n✅ 找到 {len(model_files)} 个模型文件:")
        for model_file in sorted(model_files):
            size_mb = model_file.stat().st_size / (1024 * 1024)
            print(f"   {model_file.name} ({size_mb:.2f} MB)")
        
        # 找到最新的模型
        latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
        print(f"\n📦 最新模型: {latest_model.name}")
        print(f"   完整路径: {latest_model.absolute()}")
        
        # 提取epoch号
        epoch = latest_model.stem.split('epoch')[-1]
        print(f"\n💡 建议的后端配置:")
        print(f"   MODEL_PATH={latest_model.absolute()}")
        print(f"   或相对路径: MODEL_PATH={latest_model}")
    else:
        print("\n⚠️  尚未保存模型文件（训练可能还在进行中）")
    
    # 检查metrics文件
    metrics_file = model_dir / "metrics.tsv"
    if metrics_file.exists():
        print(f"\n📊 指标文件存在: {metrics_file.name}")
        try:
            import pandas as pd
            df = pd.read_csv(metrics_file, sep='\t')
            if not df.empty:
                print(f"   包含 {len(df)} 条记录")
                best_idx = df['recall'].idxmax()
                best_epoch = df.loc[best_idx, 'epoch']
                best_recall = df.loc[best_idx, 'recall']
                print(f"   最佳epoch: {int(best_epoch)} (Recall@20: {best_recall:.4f})")
        except Exception as e:
            print(f"   无法读取指标文件: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_training_status()

