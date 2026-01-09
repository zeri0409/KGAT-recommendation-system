"""
导入amazon-book数据集到PostgreSQL和Neo4j
支持限制导入数据量以加快速度
"""
import os
import sys
import hashlib
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent  # backend的父目录（项目根目录）
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))  # backend目录

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Item, Interaction, KGTriple
from app.database_neo4j import neo4j_driver
# 导入数据生成函数（从当前目录导入）
from generate_fake_data import generate_user_data, fetch_book_info
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_train_data(file_path: str, max_users: int = None):
    """加载训练数据（用户-商品交互）
    
    Args:
        file_path: 训练数据文件路径
        max_users: 最大用户数限制，None表示不限制
    """
    user_item_dict = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if max_users and len(user_item_dict) >= max_users:
                break
            parts = line.strip().split()
            if len(parts) > 1:
                user_id = int(parts[0])
                item_ids = [int(x) for x in parts[1:]]
                user_item_dict[user_id] = item_ids
    return user_item_dict


def load_kg_data(file_path: str, max_triples: int = None):
    """加载知识图谱数据（三元组）
    
    Args:
        file_path: KG数据文件路径
        max_triples: 最大三元组数限制，None表示不限制
    """
    triples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if max_triples and len(triples) >= max_triples:
                break
            parts = line.strip().split()
            if len(parts) == 3:
                triples.append((int(parts[0]), int(parts[1]), int(parts[2])))
    return triples


def import_users(db: Session, user_ids: list, use_neo4j: bool = True):
    """导入用户数据到PostgreSQL和Neo4j"""
    logger.info("开始导入用户数据...")
    users = []
    neo4j_count = 0
    
    for user_id in tqdm(user_ids, desc="导入用户"):
        # 检查用户是否已存在
        existing = db.query(User).filter(User.user_id == user_id).first()
        if existing:
            continue

        user_data = generate_user_data(user_id)
        user = User(
            user_id=user_id,
            username=user_data['username'],
            email=user_data['email'],
            avatar_url=user_data['avatar_url'],
            password_hash=hashlib.sha256(f"password{user_id}".encode()).hexdigest(),
            role='user'
        )
        users.append(user)
        
        # 批量插入PostgreSQL
        if len(users) >= 1000:
            db.bulk_save_objects(users)
            db.commit()
            users = []
        
        # 导入到Neo4j
        if use_neo4j and neo4j_driver.is_connected():
            try:
                neo4j_driver.create_node(
                    label="User",
                    properties={
                        "user_id": user_id,
                        "username": user_data['username'],
                        "email": user_data['email'],
                        "avatar_url": user_data['avatar_url']
                    }
                )
                neo4j_count += 1
            except Exception as e:
                logger.warning(f"Neo4j导入用户{user_id}失败: {e}")
    
    # 插入剩余用户
    if users:
        db.bulk_save_objects(users)
        db.commit()
    
    logger.info(f"PostgreSQL导入 {len(user_ids)} 个用户")
    if use_neo4j:
        logger.info(f"Neo4j导入 {neo4j_count} 个用户")


def import_items(db: Session, item_ids: set, use_neo4j: bool = True, use_api: bool = False):
    """导入商品数据到PostgreSQL和Neo4j"""
    logger.info("开始导入商品数据...")
    items = []
    neo4j_count = 0
    
    for item_id in tqdm(item_ids, desc="导入商品"):
        # 检查商品是否已存在
        existing = db.query(Item).filter(Item.item_id == item_id).first()
        if existing:
            continue

        book_info = fetch_book_info(item_id, use_api=use_api)
        item = Item(
            item_id=item_id,
            title=book_info['title'],
            description=book_info.get('description', ''),
            image_url=book_info.get('image_url', ''),
            price=book_info.get('price'),
            rating=book_info.get('rating'),
            category='book'
        )
        items.append(item)
        
        # 批量插入PostgreSQL
        if len(items) >= 1000:
            db.bulk_save_objects(items)
            db.commit()
            items = []
        
        # 导入到Neo4j
        if use_neo4j and neo4j_driver.is_connected():
            try:
                neo4j_driver.create_node(
                    label="Item",
                    properties={
                        "item_id": item_id,
                        "title": book_info['title'],
                        "description": book_info.get('description', ''),
                        "image_url": book_info.get('image_url', ''),
                        "category": "book"
                    }
                )
                neo4j_count += 1
            except Exception as e:
                logger.warning(f"Neo4j导入商品{item_id}失败: {e}")
    
    # 插入剩余商品
    if items:
        db.bulk_save_objects(items)
        db.commit()
    
    logger.info(f"PostgreSQL导入 {len(item_ids)} 个商品")
    if use_neo4j:
        logger.info(f"Neo4j导入 {neo4j_count} 个商品")


def import_interactions(db: Session, user_item_dict: dict, use_neo4j: bool = True, max_interactions: int = None):
    """导入交互数据到PostgreSQL和Neo4j
    
    Args:
        max_interactions: 最大交互数限制，None表示不限制
    """
    logger.info("开始导入交互数据...")
    interactions = []
    neo4j_count = 0
    interaction_count = 0
    should_break = False
    
    for user_id, item_ids in tqdm(user_item_dict.items(), desc="导入交互"):
        if should_break:
            break
        for item_id in item_ids:
            if max_interactions and interaction_count >= max_interactions:
                should_break = True
                break
            interaction_count += 1
            interaction = Interaction(
                user_id=user_id,
                item_id=item_id,
                interaction_type='purchase',  # 训练数据中的交互视为购买
                timestamp=None
            )
            interactions.append(interaction)
            
            # 批量插入PostgreSQL
            if len(interactions) >= 10000:
                db.bulk_save_objects(interactions)
                db.commit()
                interactions = []
            
            # 导入到Neo4j（创建用户-商品关系）
            if use_neo4j and neo4j_driver.is_connected():
                try:
                    neo4j_driver.create_relationship(
                        from_label="User",
                        from_id_key="user_id",
                        from_id_value=user_id,
                        to_label="Item",
                        to_id_key="item_id",
                        to_id_value=item_id,
                        rel_type="PURCHASED",
                        properties={"interaction_type": "purchase"}
                    )
                    neo4j_count += 1
                except Exception as e:
                    if neo4j_count % 1000 == 0:  # 减少日志输出
                        logger.warning(f"Neo4j导入交互失败: {e}")
    
    # 插入剩余交互
    if interactions:
        db.bulk_save_objects(interactions)
        db.commit()
    
    logger.info(f"PostgreSQL导入交互数据完成")
    if use_neo4j:
        logger.info(f"Neo4j导入 {neo4j_count} 个交互关系")


def import_kg_triples(db: Session, triples: list, use_neo4j: bool = True, max_triples: int = None):
    """导入知识图谱三元组到PostgreSQL和Neo4j
    
    Args:
        max_triples: 最大三元组数限制，None表示不限制（如果triples已经限制过，这里可以再次限制）
    """
    logger.info("开始导入知识图谱数据...")
    kg_triples = []
    neo4j_count = 0
    triple_count = 0
    
    for head, relation, tail in tqdm(triples, desc="导入KG三元组"):
        if max_triples and triple_count >= max_triples:
            break
        triple_count += 1
        # 导入到PostgreSQL
        triple = KGTriple(
            head_entity_id=head,
            relation_id=relation,
            tail_entity_id=tail
        )
        kg_triples.append(triple)
        
        if len(kg_triples) >= 10000:
            db.bulk_save_objects(kg_triples)
            db.commit()
            kg_triples = []
        
        # 导入到Neo4j
        if use_neo4j and neo4j_driver.is_connected():
            try:
                # 创建实体节点（如果不存在）
                neo4j_driver.create_node(
                    label="Entity",
                    properties={"entity_id": head}
                )
                neo4j_driver.create_node(
                    label="Entity",
                    properties={"entity_id": tail}
                )
                
                # 创建关系
                neo4j_driver.create_relationship(
                    from_label="Entity",
                    from_id_key="entity_id",
                    from_id_value=head,
                    to_label="Entity",
                    to_id_key="entity_id",
                    to_id_value=tail,
                    rel_type=f"REL_{relation}",
                    properties={"relation_id": relation}
                )
                neo4j_count += 1
            except Exception as e:
                if neo4j_count % 1000 == 0:
                    logger.warning(f"Neo4j导入KG三元组失败: {e}")
    
    # 插入剩余三元组
    if kg_triples:
        db.bulk_save_objects(kg_triples)
        db.commit()
    
    logger.info(f"PostgreSQL导入知识图谱数据完成")
    if use_neo4j:
        logger.info(f"Neo4j导入 {neo4j_count} 个KG关系")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='导入amazon-book数据集')
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='数据集目录（默认：<repo_root>/datasets/amazon-book）'
    )
    parser.add_argument('--max-users', type=int, default=None, help='最大用户数限制（默认：不限制）')
    parser.add_argument('--max-items', type=int, default=None, help='最大商品数限制（默认：不限制）')
    parser.add_argument('--max-interactions', type=int, default=None, help='最大交互数限制（默认：不限制）')
    parser.add_argument('--max-kg-triples', type=int, default=None, help='最大KG三元组数限制（默认：不限制）')
    parser.add_argument('--skip-kg', action='store_true', help='跳过知识图谱数据导入（加快速度）')
    parser.add_argument('--skip-neo4j', action='store_true', help='跳过Neo4j导入（仅导入PostgreSQL）')
    parser.add_argument('--use-api', action='store_true', help='使用API获取真实图书信息（较慢）')
    
    args = parser.parse_args()
    
    # 默认数据集位置：仓库根目录下的 datasets/amazon-book
    # backend/scripts/import_amazon_data.py -> backend/scripts -> backend -> repo_root
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = args.data_dir or str(repo_root / "datasets" / "amazon-book")
    train_file = os.path.join(data_dir, "train.txt")
    kg_file = os.path.join(data_dir, "kg_final.txt")

    if not os.path.exists(train_file):
        logger.error(f"错误：找不到文件 {train_file}")
        return

    # 检查Neo4j连接
    use_neo4j = not args.skip_neo4j and neo4j_driver.is_connected()
    if use_neo4j:
        logger.info("Neo4j已连接，将同时导入到Neo4j")
    else:
        logger.warning("Neo4j未连接或已跳过，仅导入到PostgreSQL")

    # 显示限制信息
    if args.max_users or args.max_items or args.max_interactions or args.max_kg_triples:
        logger.info("=" * 60)
        logger.info("数据导入限制设置：")
        if args.max_users:
            logger.info(f"  最大用户数: {args.max_users}")
        if args.max_items:
            logger.info(f"  最大商品数: {args.max_items}")
        if args.max_interactions:
            logger.info(f"  最大交互数: {args.max_interactions}")
        if args.max_kg_triples:
            logger.info(f"  最大KG三元组数: {args.max_kg_triples}")
        if args.skip_kg:
            logger.info("  跳过知识图谱数据导入")
        logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 1. 加载训练数据
        logger.info("加载训练数据...")
        user_item_dict = load_train_data(train_file, max_users=args.max_users)
        user_ids = list(user_item_dict.keys())
        item_ids = set()
        for items in user_item_dict.values():
            item_ids.update(items)
        
        # 限制商品数
        if args.max_items and len(item_ids) > args.max_items:
            item_ids = set(list(item_ids)[:args.max_items])
            logger.info(f"商品数已限制为: {len(item_ids)}")

        logger.info(f"数据统计：")
        logger.info(f"  用户数: {len(user_ids)}")
        logger.info(f"  商品数: {len(item_ids)}")
        total_interactions = sum(len(items) for items in user_item_dict.values())
        logger.info(f"  交互数: {total_interactions}")

        # 2. 导入用户
        import_users(db, user_ids, use_neo4j=use_neo4j)

        # 3. 导入商品
        import_items(db, item_ids, use_neo4j=use_neo4j, use_api=args.use_api)

        # 4. 导入交互
        import_interactions(db, user_item_dict, use_neo4j=use_neo4j, max_interactions=args.max_interactions)

        # 5. 导入知识图谱（可选）
        if not args.skip_kg and os.path.exists(kg_file):
            triples = load_kg_data(kg_file, max_triples=args.max_kg_triples)
            logger.info(f"  知识图谱三元组数: {len(triples)}")
            import_kg_triples(db, triples, use_neo4j=use_neo4j, max_triples=args.max_kg_triples)
        elif args.skip_kg:
            logger.info("跳过知识图谱数据导入")
        else:
            logger.warning(f"未找到知识图谱文件: {kg_file}")

        logger.info("=" * 60)
        logger.info("数据导入完成！")
        logger.info("=" * 60)

    except Exception as e:
        db.rollback()
        logger.error(f"错误：{e}", exc_info=True)
        raise
    finally:
        db.close()
        if neo4j_driver:
            neo4j_driver.close()


if __name__ == "__main__":
    main()

