"""
简单测试PostgreSQL连接（处理编码问题）
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['PGCLIENTENCODING'] = 'UTF8'

from app.config import settings
from urllib.parse import urlparse
import psycopg2

print("=" * 60)
print("PostgreSQL连接测试")
print("=" * 60)

# 解析连接URL
db_url = settings.DATABASE_URL
parsed = urlparse(db_url)

print(f"\n连接信息:")
print(f"  主机: {parsed.hostname}")
print(f"  端口: {parsed.port or 5432}")
print(f"  用户: {parsed.username}")
print(f"  数据库: {parsed.path[1:] if parsed.path else '未指定'}")

print(f"\n正在测试连接...")

try:
    # 直接使用psycopg2连接，设置编码
    conn = psycopg2.connect(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:] if parsed.path else 'kgat_recommendation',
        connect_timeout=5
    )
    
    # 设置客户端编码
    conn.set_client_encoding('UTF8')
    
    cursor = conn.cursor()
    
    # 测试查询
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"\n✅ 连接成功！")
    print(f"   PostgreSQL版本: {version.split(',')[0]}")
    
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]
    print(f"   当前数据库: {db_name}")
    
    cursor.execute("SELECT current_user;")
    current_user = cursor.fetchone()[0]
    print(f"   当前用户: {current_user}")
    
    cursor.close()
    conn.close()
    
    print(f"\n✅ PostgreSQL连接正常，可以初始化数据库！")
    print(f"\n下一步: python scripts/init_database.py")
    
except psycopg2.OperationalError as e:
    error_str = str(e)
    print(f"\n❌ 连接失败")
    
    if "password authentication failed" in error_str.lower():
        print("\n可能的原因：密码错误或用户不存在")
        print("\n解决方法：")
        print("  1. 使用postgres用户连接: psql -U postgres")
        print("  2. 创建用户: CREATE USER postgres WITH PASSWORD 'kgat_password';")
        print("  3. 创建数据库: CREATE DATABASE kgat_recommendation;")
        print("  4. 授予权限:")
        print("     GRANT ALL PRIVILEGES ON DATABASE kgat_recommendation TO postgres;")
        print("     \\c kgat_recommendation")
        print("     GRANT ALL ON SCHEMA public TO postgres;")
    elif "database" in error_str.lower() and "does not exist" in error_str.lower():
        print("\n可能的原因：数据库不存在")
        print("\n解决方法：")
        print("  1. 使用postgres用户连接: psql -U postgres")
        print("  2. 创建数据库: CREATE DATABASE kgat_recommendation;")
        print("  3. 授予权限: GRANT ALL PRIVILEGES ON DATABASE kgat_recommendation TO postgres;")
    elif "could not connect" in error_str.lower():
        print("\n可能的原因：PostgreSQL服务未启动")
        print("\n解决方法：")
        print("  1. 检查PostgreSQL服务是否运行")
        print("  2. Windows: 打开服务管理器(services.msc)，查找PostgreSQL服务")
    else:
        print(f"\n错误详情: {error_str[:200]}")
        
except UnicodeDecodeError as e:
    print(f"\n⚠️ 编码错误: {e}")
    print("   这可能是PostgreSQL返回的错误消息使用了非UTF-8编码")
    print("\n建议：")
    print("  1. 先使用psql命令行工具测试连接:")
    print("     psql -U postgres -d kgat_recommendation -h localhost")
    print("  2. 如果psql可以连接，说明配置正确，只是Python编码问题")
    print("  3. 数据库连接配置已添加UTF8编码设置，请重试")
    
except Exception as e:
    print(f"\n❌ 错误: {type(e).__name__}")
    print(f"   详情: {repr(e)[:200]}")

print("\n" + "=" * 60)

