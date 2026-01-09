"""
诊断PostgreSQL连接问题
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from urllib.parse import urlparse

print("=" * 70)
print("PostgreSQL连接问题诊断")
print("=" * 70)

# 解析连接信息
db_url = settings.DATABASE_URL
parsed = urlparse(db_url)

print(f"\n📋 配置信息:")
print(f"  主机: {parsed.hostname}")
print(f"  端口: {parsed.port or 5432}")
print(f"  用户: {parsed.username}")
print(f"  数据库: {parsed.path[1:] if parsed.path else '未指定'}")

print(f"\n🔍 问题分析:")
print(f"  错误: UnicodeDecodeError - PostgreSQL返回的错误消息使用了非UTF-8编码")
print(f"  原因: PostgreSQL服务器可能使用GBK或Windows-1252编码返回错误消息")

print(f"\n✅ 解决方案:")
print(f"\n方案1: 使用psql命令行工具测试连接（推荐）")
print(f"  运行以下命令:")
print(f"    psql -U postgres -d kgat_recommendation -h localhost")
print(f"  输入密码: kgat_password")
print(f"\n  如果连接成功:")
print(f"    - 说明数据库和用户存在，配置正确")
print(f"    - 可以尝试直接运行: python scripts/init_database.py")
print(f"    - 如果仍有编码错误，使用方案2")
print(f"\n  如果连接失败:")
print(f"    - 说明用户或数据库不存在，需要创建（见方案3）")

print(f"\n方案2: 修改PostgreSQL服务器编码（如果psql可以连接）")
print(f"  1. 连接到PostgreSQL:")
print(f"     psql -U postgres")
print(f"  2. 检查数据库编码:")
print(f"     \\l kgat_recommendation")
print(f"  3. 如果编码不是UTF8，修改数据库编码:")
print(f"     ALTER DATABASE kgat_recommendation SET client_encoding = 'UTF8';")

print(f"\n方案3: 创建用户和数据库（如果用户/数据库不存在）")
print(f"  1. 使用postgres用户连接:")
print(f"     psql -U postgres")
print(f"  2. 创建用户:")
print(f"     CREATE USER postgres WITH PASSWORD 'kgat_password';")
print(f"  3. 创建数据库（使用UTF8编码）:")
print(f"     CREATE DATABASE kgat_recommendation WITH ENCODING 'UTF8';")
print(f"  4. 授予权限:")
print(f"     GRANT ALL PRIVILEGES ON DATABASE kgat_recommendation TO postgres;")
print(f"  5. 连接到新数据库:")
print(f"     \\c kgat_recommendation")
print(f"  6. 授予schema权限:")
print(f"     GRANT ALL ON SCHEMA public TO postgres;")

print(f"\n方案4: 使用SQLAlchemy的事件监听器（临时解决方案）")
print(f"  已在database.py中添加UTF8编码设置")
print(f"  如果仍有问题，可以尝试直接运行init_database.py")

print(f"\n" + "=" * 70)
print(f"\n💡 建议:")
print(f"  1. 先运行方案1，使用psql测试连接")
print(f"  2. 根据psql的结果，选择对应的解决方案")
print(f"  3. 如果psql可以连接，说明只是Python编码问题，可以尝试直接运行:")
print(f"     python scripts/init_database.py")

print(f"\n" + "=" * 70)

