"""
检查所有数据库（PostgreSQL、Redis、Neo4j）的数据导入情况
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models import User, Item, Interaction, KGTriple, Recommendation
from app.config import settings
from sqlalchemy import func, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入Redis和Neo4j
try:
    import redis
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    REDIS_AVAILABLE = True
except Exception as e:
    REDIS_AVAILABLE = False
    redis_error = str(e)

try:
    from app.database_neo4j import neo4j_driver
    NEO4J_AVAILABLE = neo4j_driver.is_connected() if neo4j_driver and hasattr(neo4j_driver, 'is_connected') else False
    neo4j_driver_obj = neo4j_driver.driver if hasattr(neo4j_driver, 'driver') else None
except Exception as e:
    NEO4J_AVAILABLE = False
    neo4j_error = str(e)
    neo4j_driver_obj = None


def check_postgresql():
    """检查PostgreSQL数据"""
    print("\n" + "=" * 70)
    print("📊 PostgreSQL 数据统计")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # 用户数据
        user_count = db.query(func.count(User.user_id)).scalar()
        min_user = db.query(func.min(User.user_id)).scalar() or 0
        max_user = db.query(func.max(User.user_id)).scalar() or 0
        
        # 商品数据
        item_count = db.query(func.count(Item.item_id)).scalar()
        min_item = db.query(func.min(Item.item_id)).scalar() or 0
        max_item = db.query(func.max(Item.item_id)).scalar() or 0
        
        # 交互数据
        interaction_count = db.query(func.count(Interaction.interaction_id)).scalar()
        users_with_interactions = db.query(func.count(func.distinct(Interaction.user_id))).scalar()
        items_with_interactions = db.query(func.count(func.distinct(Interaction.item_id))).scalar()
        
        # KG数据
        kg_count = db.query(func.count(KGTriple.head_entity_id)).scalar()
        relation_types = db.query(
            func.count(func.distinct(KGTriple.relation_id))
        ).scalar()
        
        # 推荐数据
        recommendation_count = db.query(func.count(Recommendation.recommendation_id)).scalar()
        
        print(f"\n👥 用户数据:")
        print(f"   总数: {user_count:,}")
        print(f"   ID范围: {min_user} - {max_user}")
        
        print(f"\n📦 商品数据:")
        print(f"   总数: {item_count:,}")
        print(f"   ID范围: {min_item} - {max_item}")
        
        print(f"\n🔄 交互数据:")
        print(f"   总数: {interaction_count:,}")
        print(f"   有交互的用户: {users_with_interactions:,}")
        print(f"   有交互的商品: {items_with_interactions:,}")
        if user_count > 0:
            print(f"   平均每用户交互数: {interaction_count/user_count:.2f}")
        
        print(f"\n🔗 知识图谱数据:")
        print(f"   三元组总数: {kg_count:,}")
        print(f"   关系类型数: {relation_types}")
        
        print(f"\n💡 推荐数据:")
        print(f"   推荐记录数: {recommendation_count:,}")
        
        return {
            "users": user_count,
            "items": item_count,
            "interactions": interaction_count,
            "kg_triples": kg_count,
            "recommendations": recommendation_count
        }
        
    except Exception as e:
        print(f"❌ PostgreSQL检查失败: {e}")
        return None
    finally:
        db.close()


def check_redis():
    """检查Redis数据"""
    print("\n" + "=" * 70)
    print("🔴 Redis 数据统计")
    print("=" * 70)
    
    if not REDIS_AVAILABLE:
        print(f"\n⚠️ Redis不可用: {redis_error if 'redis_error' in locals() else '未安装或未连接'}")
        return None
    
    try:
        # 测试连接
        redis_client.ping()
        
        # 获取所有键
        keys = redis_client.keys("*")
        key_count = len(keys)
        
        print(f"\n📊 键统计:")
        print(f"   总键数: {key_count}")
        
        if key_count > 0:
            # 按前缀分类
            key_prefixes = {}
            for key in keys:
                prefix = key.split(':')[0] if ':' in key else key
                key_prefixes[prefix] = key_prefixes.get(prefix, 0) + 1
            
            print(f"\n   键类型分布:")
            for prefix, count in sorted(key_prefixes.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"     {prefix}: {count}")
            
            # 检查推荐缓存
            recommendation_keys = [k for k in keys if 'recommendation' in k.lower() or 'rec' in k.lower()]
            print(f"\n   推荐相关键: {len(recommendation_keys)}")
            
            # 获取内存使用
            try:
                info = redis_client.info('memory')
                used_memory = info.get('used_memory_human', 'N/A')
                print(f"\n💾 内存使用: {used_memory}")
            except:
                pass
        
        return {"keys": key_count}
        
    except Exception as e:
        print(f"❌ Redis检查失败: {e}")
        return None


def check_neo4j():
    """检查Neo4j数据"""
    print("\n" + "=" * 70)
    print("🟢 Neo4j 数据统计")
    print("=" * 70)
    
    if not NEO4J_AVAILABLE:
        print(f"\n⚠️ Neo4j不可用: {neo4j_error if 'neo4j_error' in locals() else '未安装或未连接'}")
        print(f"   访问 http://localhost:7474 查看Neo4j Browser")
        return None
    
    try:
        if not neo4j_driver_obj:
            print(f"\n⚠️ Neo4j驱动不可用")
            return None
        
        with neo4j_driver_obj.session() as session:
            # 统计节点
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # 统计关系
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            # 统计节点类型
            node_types_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            node_types = {record["label"]: record["count"] for record in node_types_result}
            
            # 统计关系类型
            rel_types_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                LIMIT 10
            """)
            rel_types = {record["type"]: record["count"] for record in rel_types_result}
            
            print(f"\n📊 节点统计:")
            print(f"   总节点数: {node_count:,}")
            print(f"\n   节点类型分布:")
            for label, count in node_types.items():
                print(f"     {label}: {count:,}")
            
            print(f"\n🔗 关系统计:")
            print(f"   总关系数: {rel_count:,}")
            print(f"\n   关系类型分布（前10）:")
            for rel_type, count in rel_types.items():
                print(f"     {rel_type}: {count:,}")
            
            # 检查是否有用户-商品关系
            user_item_rel = session.run("""
                MATCH (u:User)-[r]->(i:Item)
                RETURN count(r) as count
            """).single()
            if user_item_rel:
                print(f"\n   用户-商品关系: {user_item_rel['count']:,}")
            
            return {
                "nodes": node_count,
                "relationships": rel_count,
                "node_types": node_types,
                "rel_types": rel_types
            }
            
    except Exception as e:
        print(f"❌ Neo4j检查失败: {e}")
        return None


def generate_summary(pg_data, redis_data, neo4j_data):
    """生成汇总报告"""
    print("\n" + "=" * 70)
    print("📋 数据导入情况汇总")
    print("=" * 70)
    
    print(f"\n✅ PostgreSQL:")
    if pg_data:
        print(f"   用户: {pg_data.get('users', 0):,}")
        print(f"   商品: {pg_data.get('items', 0):,}")
        print(f"   交互: {pg_data.get('interactions', 0):,}")
        print(f"   KG三元组: {pg_data.get('kg_triples', 0):,}")
    else:
        print("   ❌ 检查失败")
    
    print(f"\n✅ Redis:")
    if redis_data:
        print(f"   键数: {redis_data.get('keys', 0):,}")
    else:
        print("   ⚠️ 未连接或为空")
    
    print(f"\n✅ Neo4j:")
    if neo4j_data:
        print(f"   节点数: {neo4j_data.get('nodes', 0):,}")
        print(f"   关系数: {neo4j_data.get('relationships', 0):,}")
    else:
        print("   ⚠️ 未连接或为空")
    
    print("\n" + "=" * 70)


def print_visualization_guide():
    """打印可视化工具使用指南"""
    print("\n" + "=" * 70)
    print("📊 可视化工具使用指南")
    print("=" * 70)
    
    print("\n1️⃣ PostgreSQL 可视化:")
    print("   - pgAdmin: https://www.pgadmin.org/")
    print("   - DBeaver: https://dbeaver.io/")
    print("   - DataGrip: https://www.jetbrains.com/datagrip/")
    print("   - 命令行: psql -U postgres -d kgat_recommendation")
    
    print("\n2️⃣ Redis 可视化:")
    print("   - RedisInsight: https://redis.com/redis-enterprise/redis-insight/")
    print("   - Another Redis Desktop Manager: https://github.com/qishibo/AnotherRedisDesktopManager")
    print("   - 命令行: redis-cli")
    print("     查看所有键: KEYS *")
    print("     查看键数量: DBSIZE")
    
    print("\n3️⃣ Neo4j 可视化:")
    print("   - Neo4j Browser: http://localhost:7474")
    print("     用户名: neo4j")
    print("     密码: password (或你在.env中配置的密码)")
    print("   - 常用查询:")
    print("     查看所有节点: MATCH (n) RETURN n LIMIT 25")
    print("     查看用户节点: MATCH (u:User) RETURN u LIMIT 10")
    print("     查看商品节点: MATCH (i:Item) RETURN i LIMIT 10")
    print("     查看用户-商品关系: MATCH (u:User)-[r]->(i:Item) RETURN u, r, i LIMIT 10")
    print("     统计节点: MATCH (n) RETURN labels(n), count(n)")
    print("     统计关系: MATCH ()-[r]->() RETURN type(r), count(r)")
    
    print("\n" + "=" * 70)


def main():
    """主函数"""
    print("=" * 70)
    print("🔍 所有数据库数据导入情况检查")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 检查各数据库
    pg_data = check_postgresql()
    redis_data = check_redis()
    neo4j_data = check_neo4j()
    
    # 生成汇总
    generate_summary(pg_data, redis_data, neo4j_data)
    
    # 打印可视化指南
    print_visualization_guide()
    
    print("\n✅ 检查完成！")


if __name__ == "__main__":
    main()

