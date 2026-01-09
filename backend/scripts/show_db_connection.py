"""
显示当前数据库连接信息
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from urllib.parse import urlparse

print("=" * 70)
print("当前数据库连接信息")
print("=" * 70)

db_url = settings.DATABASE_URL
parsed = urlparse(db_url)

print(f"\n连接配置:")
print(f"  主机: {parsed.hostname}")
print(f"  端口: {parsed.port or 5432}")
print(f"  用户: {parsed.username}")
print(f"  数据库: {parsed.path[1:] if parsed.path else '未指定'}")

# 隐藏密码显示
if parsed.password:
    masked_url = db_url.replace(f':{parsed.password}@', ':****@')
else:
    masked_url = db_url
print(f"\n完整连接URL:")
print(f"  {masked_url}")

print(f"\n配置文件来源:")
print(f"  .env文件: {Path(project_root / '.env').exists()}")
print(f"  config.py默认值: {Path(project_root / 'app' / 'config.py').exists()}")

print("\n" + "=" * 70)

