#!/usr/bin/env python
"""
配置KGAT模型路径
"""
import os
import sys
from pathlib import Path

def find_model_files():
    """查找所有可能的模型文件"""
    model_files = []
    
    # 搜索常见位置
    search_paths = [
        Path("trained_model"),
        Path("."),
        Path("backend"),
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            for pth_file in search_path.rglob("*.pth"):
                model_files.append(pth_file.absolute())
    
    return model_files

def configure_model_path(model_path: str):
    """配置模型路径到后端"""
    model_path = Path(model_path).absolute()
    
    if not model_path.exists():
        print(f"❌ 错误: 模型文件不存在: {model_path}")
        return False
    
    print(f"✅ 找到模型文件: {model_path}")
    print(f"   文件大小: {model_path.stat().st_size / (1024*1024):.2f} MB")
    
    # 更新 .env 文件
    env_file = Path("backend/.env")
    env_example = Path("backend/env.example")
    
    # 如果.env不存在，从env.example复制
    if not env_file.exists() and env_example.exists():
        print(f"\n📋 创建 .env 文件（从 env.example 复制）...")
        import shutil
        shutil.copy(env_example, env_file)
    
    if env_file.exists():
        # 读取现有配置
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 更新MODEL_PATH
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith('MODEL_PATH='):
                # 使用相对路径（相对于项目根目录）
                try:
                    rel_path = os.path.relpath(model_path, Path("backend").absolute())
                    # 如果相对路径太长，使用绝对路径
                    if len(rel_path) > 100 or '..' in rel_path:
                        rel_path = str(model_path)
                    new_lines.append(f'MODEL_PATH={rel_path}\n')
                except:
                    new_lines.append(f'MODEL_PATH={model_path}\n')
                updated = True
            elif line.startswith('USE_KGAT_MODEL='):
                new_lines.append('USE_KGAT_MODEL=True\n')
            else:
                new_lines.append(line)
        
        # 如果没有找到MODEL_PATH行，添加它
        if not updated:
            rel_path = os.path.relpath(model_path, Path("backend").absolute())
            if len(rel_path) > 100 or '..' in rel_path:
                rel_path = str(model_path)
            new_lines.append(f'\n# ML模型配置\n')
            new_lines.append(f'MODEL_PATH={rel_path}\n')
            new_lines.append(f'USE_KGAT_MODEL=True\n')
        
        # 写入文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"\n✅ 已更新 {env_file}")
        print(f"   MODEL_PATH={rel_path if 'rel_path' in locals() else model_path}")
    else:
        print(f"\n⚠️  {env_file} 不存在，请手动创建或从 env.example 复制")
        print(f"   然后添加: MODEL_PATH={model_path}")
    
    # 也更新config.py的默认值（可选）
    config_file = Path("backend/app/config.py")
    if config_file.exists():
        print(f"\n💡 提示: 你也可以直接修改 {config_file} 中的 MODEL_PATH 默认值")
    
    return True

def main():
    print("=" * 60)
    print("KGAT模型路径配置工具")
    print("=" * 60)
    
    # 查找现有模型文件
    model_files = find_model_files()
    
    if model_files:
        print(f"\n📦 找到 {len(model_files)} 个模型文件:")
        for i, model_file in enumerate(model_files, 1):
            size_mb = model_file.stat().st_size / (1024 * 1024)
            print(f"   {i}. {model_file} ({size_mb:.2f} MB)")
        
        print("\n选项:")
        print("  1. 从列表中选择")
        print("  2. 手动输入路径")
        choice = input("\n请选择 (1/2): ").strip()
        
        if choice == "1":
            try:
                idx = int(input(f"请输入序号 (1-{len(model_files)}): ")) - 1
                if 0 <= idx < len(model_files):
                    model_path = model_files[idx]
                else:
                    print("❌ 无效的序号")
                    return
            except ValueError:
                print("❌ 无效的输入")
                return
        else:
            model_path = input("请输入模型文件的完整路径: ").strip().strip('"').strip("'")
            model_path = Path(model_path)
    else:
        print("\n⚠️  未找到模型文件，请手动输入路径")
        model_path = input("请输入模型文件的完整路径: ").strip().strip('"').strip("'")
        model_path = Path(model_path)
    
    # 配置模型路径
    if configure_model_path(str(model_path)):
        print("\n" + "=" * 60)
        print("✅ 配置完成！")
        print("\n下一步:")
        print("  1. 检查配置: cd backend && python scripts/init_kgat_model.py")
        print("  2. 启动服务: cd backend && uvicorn app.main:app --reload")
        print("=" * 60)

if __name__ == "__main__":
    main()

