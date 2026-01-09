"""
检查数据库配置和连接
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal, engine
from app.database_neo4j import neo4j_driver
from app.config import settings
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_postgresql():
    """检查PostgreSQL连接"""
    logger.info("检查PostgreSQL连接...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"✅ PostgreSQL连接成功")
            logger.info(f"   版本: {version}")
            
            # 检查数据库
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            logger.info(f"   当前数据库: {db_name}")
            
            # 检查表
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            logger.info(f"   表数量: {len(tables)}")
            if tables:
                logger.info(f"   表列表: {', '.join(tables)}")
            
            return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL连接失败: {e}")
        return False


def check_redis():
    """检查Redis连接"""
    logger.info("检查Redis连接...")
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        redis_client.ping()
        logger.info(f"✅ Redis连接成功")
        logger.info(f"   主机: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Redis连接失败: {e}（可选，不影响运行）")
        return False


def check_neo4j():
    """检查Neo4j连接"""
    logger.info("检查Neo4j连接...")
    try:
        if neo4j_driver.is_connected():
            logger.info(f"✅ Neo4j连接成功")
            logger.info(f"   URI: {settings.NEO4J_URI}")
            return True
        else:
            logger.warning(f"⚠️ Neo4j未连接（可选，不影响运行）")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Neo4j连接失败: {e}（可选，不影响运行）")
        return False


def check_data():
    """检查数据库中的数据"""
    logger.info("检查数据库数据...")
    db = SessionLocal()
    try:
        from app.models import User, Item, Interaction, KGTriple
        
        n_users = db.query(User).count()
        n_items = db.query(Item).count()
        n_interactions = db.query(Interaction).count()
        n_kg_triples = db.query(KGTriple).count()
        
        logger.info(f"数据统计:")
        logger.info(f"   用户数: {n_users}")
        logger.info(f"   商品数: {n_items}")
        logger.info(f"   交互数: {n_interactions}")
        logger.info(f"   KG三元组数: {n_kg_triples}")
        
        if n_users == 0 or n_items == 0:
            logger.warning("⚠️ 数据库中没有数据，请运行数据导入脚本")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 检查数据失败: {e}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("数据库配置检查")
    logger.info("=" * 50)
    
    results = {
        "PostgreSQL": check_postgresql(),
        "Redis": check_redis(),
        "Neo4j": check_neo4j(),
        "数据": check_data()
    }
    
    logger.info("=" * 50)
    logger.info("检查结果汇总:")
    for name, result in results.items():
        status = "✅ 正常" if result else "❌ 异常"
        logger.info(f"   {name}: {status}")
    
    if not results["PostgreSQL"]:
        logger.error("\n❌ PostgreSQL连接失败，请检查配置")
        return False
    
    if not results["数据"]:
        logger.warning("\n⚠️ 数据库中没有数据，请运行: python scripts/import_amazon_data.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

