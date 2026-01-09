"""
检查所有数据库配置
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("数据库配置完整检查")
print("=" * 70)

# 读取.env文件
env_path = project_root / ".env"
if not env_path.exists():
    print("❌ .env文件不存在！")
    sys.exit(1)

print(f"\n✅ .env文件存在: {env_path}")

# 解析.env文件
env_vars = {}
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()

print(f"\n📋 配置项总数: {len(env_vars)}")

# 检查必需配置
required_configs = {
    'DATABASE_URL': 'PostgreSQL数据库连接',
    'REDIS_HOST': 'Redis主机',
    'REDIS_PORT': 'Redis端口',
    'NEO4J_URI': 'Neo4j URI',
    'NEO4J_USER': 'Neo4j用户名',
    'NEO4J_PASSWORD': 'Neo4j密码',
}

print("\n" + "=" * 70)
print("配置项检查")
print("=" * 70)

for key, desc in required_configs.items():
    if key in env_vars:
        value = env_vars[key]
        if 'PASSWORD' in key:
            display_value = '*' * len(value)
        elif 'URL' in key and '@' in value:
            # 隐藏密码
            parts = value.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split('://')[1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    password = user_pass.split(':')[1]
                    display_value = value.replace(f':{password}', ':****')
                else:
                    display_value = value
            else:
                display_value = value
        else:
            display_value = value
        print(f"✅ {key:20s} = {display_value:40s} ({desc})")
    else:
        print(f"❌ {key:20s} = {'缺失':40s} ({desc})")

# 详细解析PostgreSQL配置
print("\n" + "=" * 70)
print("PostgreSQL配置详情")
print("=" * 70)

if 'DATABASE_URL' in env_vars:
    db_url = env_vars['DATABASE_URL']
    try:
        parsed = urlparse(db_url)
        print(f"协议:     {parsed.scheme}")
        print(f"用户名:   {parsed.username}")
        print(f"密码:     {'*' * len(parsed.password) if parsed.password else '未设置'}")
        print(f"主机:     {parsed.hostname}")
        print(f"端口:     {parsed.port or '默认(5432)'}")
        print(f"数据库:   {parsed.path[1:] if parsed.path else '未指定'}")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
else:
    print("❌ DATABASE_URL未配置")

# 详细解析Redis配置
print("\n" + "=" * 70)
print("Redis配置详情")
print("=" * 70)

redis_host = env_vars.get('REDIS_HOST', 'localhost')
redis_port = env_vars.get('REDIS_PORT', '6379')
redis_db = env_vars.get('REDIS_DB', '0')
print(f"主机:     {redis_host}")
print(f"端口:     {redis_port}")
print(f"数据库:   {redis_db}")

# 详细解析Neo4j配置
print("\n" + "=" * 70)
print("Neo4j配置详情")
print("=" * 70)

neo4j_uri = env_vars.get('NEO4J_URI', 'bolt://localhost:7687')
neo4j_user = env_vars.get('NEO4J_USER', 'neo4j')
neo4j_password = env_vars.get('NEO4J_PASSWORD', '')
print(f"URI:      {neo4j_uri}")
print(f"用户名:   {neo4j_user}")
print(f"密码:     {'*' * len(neo4j_password) if neo4j_password else '未设置'}")

# 测试连接
print("\n" + "=" * 70)
print("连接测试")
print("=" * 70)

# PostgreSQL
print("\n🔌 测试PostgreSQL连接...")
try:
    import psycopg2
    parsed = urlparse(env_vars.get('DATABASE_URL', ''))
    conn = psycopg2.connect(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:] if parsed.path else 'kgat_recommendation',
        connect_timeout=5
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    print(f"   ✅ PostgreSQL连接成功！")
    print(f"   版本: {version.split(',')[0]}")
    print(f"   当前数据库: {db_name}")
except ImportError:
    print("   ⚠️ psycopg2未安装，无法测试连接")
    print("   请运行: pip install psycopg2-binary")
except Exception as e:
    print(f"   ❌ PostgreSQL连接失败: {e}")
    print("\n   可能的原因：")
    print("   1. PostgreSQL服务未启动")
    print("   2. 用户名或密码错误")
    print("   3. 数据库不存在")
    print("   4. 端口被占用或防火墙阻止")
    print("\n   解决方法：")
    print("   1. 检查PostgreSQL服务是否运行")
    print("   2. 确认用户和数据库是否存在：")
    print("      psql -U postgres")
    print("      CREATE USER postgres WITH PASSWORD 'kgat_password';")
    print("      CREATE DATABASE kgat_recommendation;")
    print("      GRANT ALL PRIVILEGES ON DATABASE kgat_recommendation TO postgres;")

# Redis
print("\n🔌 测试Redis连接...")
try:
    import redis
    redis_client = redis.Redis(
        host=redis_host,
        port=int(redis_port),
        db=int(redis_db),
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    print(f"   ✅ Redis连接成功！")
    print(f"   主机: {redis_host}:{redis_port}")
except ImportError:
    print("   ⚠️ redis未安装，无法测试连接")
    print("   请运行: pip install redis")
except Exception as e:
    print(f"   ⚠️ Redis连接失败: {e}（可选，不影响运行）")
    print("   如果Redis未安装，可以跳过此服务")

# Neo4j
print("\n🔌 测试Neo4j连接...")
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
        connection_timeout=5
    )
    with driver.session() as session:
        result = session.run("RETURN 1 as test")
        result.single()
    driver.close()
    print(f"   ✅ Neo4j连接成功！")
    print(f"   URI: {neo4j_uri}")
except ImportError:
    print("   ⚠️ neo4j未安装，无法测试连接")
    print("   请运行: pip install neo4j")
except Exception as e:
    print(f"   ⚠️ Neo4j连接失败: {e}（可选，不影响运行）")
    print("   如果Neo4j未安装，可以跳过此服务")
    print("   或访问 http://localhost:7474 检查Neo4j Browser是否可访问")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)

