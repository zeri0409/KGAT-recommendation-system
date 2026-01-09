"""
检查数据导入情况
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models import User, Item, Interaction, KGTriple, Recommendation
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_import_status():
    """检查数据导入情况"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("数据导入情况检查")
        print("=" * 70)
        
        # 1. 检查用户数据
        user_count = db.query(func.count(User.user_id)).scalar()
        print(f"\n📊 用户数据:")
        print(f"   用户总数: {user_count}")
        
        if user_count > 0:
            # 获取用户ID范围
            min_user = db.query(func.min(User.user_id)).scalar()
            max_user = db.query(func.max(User.user_id)).scalar()
            print(f"   用户ID范围: {min_user} - {max_user}")
        
        # 2. 检查商品数据
        item_count = db.query(func.count(Item.item_id)).scalar()
        print(f"\n📦 商品数据:")
        print(f"   商品总数: {item_count}")
        
        if item_count > 0:
            # 获取商品ID范围
            min_item = db.query(func.min(Item.item_id)).scalar()
            max_item = db.query(func.max(Item.item_id)).scalar()
            print(f"   商品ID范围: {min_item} - {max_item}")
            
            # 检查有标题的商品数
            items_with_title = db.query(func.count(Item.item_id)).filter(Item.title.isnot(None)).scalar()
            print(f"   有标题的商品: {items_with_title}")
        
        # 3. 检查交互数据
        interaction_count = db.query(func.count(Interaction.interaction_id)).scalar()
        print(f"\n🔄 交互数据:")
        print(f"   交互总数: {interaction_count}")
        
        if interaction_count > 0:
            # 统计交互类型
            interaction_types = db.query(
                Interaction.interaction_type,
                func.count(Interaction.interaction_id)
            ).group_by(Interaction.interaction_type).all()
            
            print(f"   交互类型分布:")
            for inter_type, count in interaction_types:
                print(f"     {inter_type}: {count}")
            
            # 统计有交互的用户数
            users_with_interactions = db.query(func.count(func.distinct(Interaction.user_id))).scalar()
            print(f"   有交互的用户数: {users_with_interactions}")
            
            # 统计有交互的商品数
            items_with_interactions = db.query(func.count(func.distinct(Interaction.item_id))).scalar()
            print(f"   有交互的商品数: {items_with_interactions}")
        
        # 4. 检查知识图谱数据
        kg_count = db.query(func.count(KGTriple.head_entity_id)).scalar()
        print(f"\n🔗 知识图谱数据:")
        print(f"   KG三元组总数: {kg_count}")
        
        if kg_count > 0:
            # 统计关系类型
            relation_counts = db.query(
                KGTriple.relation_id,
                func.count(KGTriple.head_entity_id)
            ).group_by(KGTriple.relation_id).order_by(KGTriple.relation_id).all()
            
            print(f"   关系类型分布:")
            for relation_id, count in relation_counts[:10]:  # 只显示前10个
                print(f"     关系ID {relation_id}: {count} 个三元组")
            if len(relation_counts) > 10:
                print(f"     ... 还有 {len(relation_counts) - 10} 种关系类型")
            
            # 统计唯一实体数（使用更简单的方式）
            head_entities = db.query(func.count(func.distinct(KGTriple.head_entity_id))).scalar()
            tail_entities = db.query(func.count(func.distinct(KGTriple.tail_entity_id))).scalar()
            print(f"   唯一头实体数: {head_entities}")
            print(f"   唯一尾实体数: {tail_entities}")
            
            # 使用SQL UNION统计总唯一实体数
            from sqlalchemy import text
            result = db.execute(text("""
                SELECT COUNT(DISTINCT entity_id) as total_entities
                FROM (
                    SELECT head_entity_id as entity_id FROM kg_triples
                    UNION
                    SELECT tail_entity_id as entity_id FROM kg_triples
                ) as all_entities
            """))
            total_entities = result.scalar()
            print(f"   总唯一实体数: {total_entities}")
        
        # 5. 检查推荐数据
        recommendation_count = db.query(func.count(Recommendation.recommendation_id)).scalar()
        print(f"\n💡 推荐数据:")
        print(f"   推荐记录总数: {recommendation_count}")
        
        # 6. 数据完整性检查
        print(f"\n✅ 数据完整性检查:")
        has_users = user_count > 0
        has_items = item_count > 0
        has_interactions = interaction_count > 0
        has_kg = kg_count > 0
        
        print(f"   用户数据: {'✅' if has_users else '❌'}")
        print(f"   商品数据: {'✅' if has_items else '❌'}")
        print(f"   交互数据: {'✅' if has_interactions else '❌'}")
        print(f"   KG数据: {'✅' if has_kg else '❌'}")
        
        # 7. 数据比例分析
        if has_users and has_items and has_interactions:
            print(f"\n📈 数据比例分析:")
            avg_interactions_per_user = interaction_count / user_count if user_count > 0 else 0
            avg_interactions_per_item = interaction_count / item_count if item_count > 0 else 0
            print(f"   平均每个用户的交互数: {avg_interactions_per_user:.2f}")
            print(f"   平均每个商品的交互数: {avg_interactions_per_item:.2f}")
            
            if has_kg:
                kg_per_item_ratio = kg_count / item_count if item_count > 0 else 0
                print(f"   KG三元组/商品比例: {kg_per_item_ratio:.2f}")
        
        # 8. 导入进度估算（如果知道总数据量）
        print(f"\n📊 导入进度估算:")
        print(f"   注意: 以下为amazon-book数据集的完整规模")
        print(f"   完整数据集规模:")
        print(f"     - 用户数: ~70,000")
        print(f"     - 商品数: ~25,000")
        print(f"     - 交互数: ~847,000")
        print(f"     - KG三元组数: ~2,557,746")
        
        if has_users:
            user_progress = (user_count / 70000) * 100 if user_count < 70000 else 100
            print(f"\n   当前进度:")
            print(f"     用户: {user_count}/70,000 ({user_progress:.1f}%)")
        
        if has_items:
            item_progress = (item_count / 25000) * 100 if item_count < 25000 else 100
            print(f"     商品: {item_count}/25,000 ({item_progress:.1f}%)")
        
        if has_kg:
            kg_progress = (kg_count / 2557746) * 100 if kg_count < 2557746 else 100
            print(f"     KG三元组: {kg_count:,}/2,557,746 ({kg_progress:.2f}%)")
        
        print("\n" + "=" * 70)
        
        # 9. 建议
        if not has_users or not has_items:
            print("\n⚠️ 建议:")
            print("   数据不完整，请运行数据导入脚本:")
            print("   python scripts/import_amazon_data.py")
        elif not has_interactions:
            print("\n⚠️ 建议:")
            print("   缺少交互数据，请运行数据导入脚本导入交互数据")
        elif not has_kg:
            print("\n💡 提示:")
            print("   未导入KG数据，如果需要KGAT模型，请导入KG数据")
            print("   或使用: python scripts/import_amazon_data.py --max-kg-triples 50000")
        else:
            print("\n✅ 数据导入完整，可以开始使用推荐系统！")
        
    except Exception as e:
        logger.error(f"检查失败: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    check_import_status()

