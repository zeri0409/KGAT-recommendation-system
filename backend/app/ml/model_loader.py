"""
模型加载和初始化工具
"""
import os
import sys
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.ml.kgat_predictor import KGATPredictor, reload_predictor
from app.ml.data_adapter import DataAdapter
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def initialize_kgat_model(
    model_path: Optional[str] = None,
    db: Optional[Session] = None
) -> KGATPredictor:
    """
    初始化KGAT模型并构建图
    
    Args:
        model_path: 模型文件路径
        db: 数据库会话
    
    Returns:
        KGAT预测器实例
    """
    if model_path is None:
        model_path = settings.MODEL_PATH
    
    if not model_path or not os.path.exists(model_path):
        logger.warning(f"模型文件不存在: {model_path}")
        return None
    
    # 确保有数据库会话
    if db is None:
        db = SessionLocal()
        should_close_db = True
    else:
        should_close_db = False
    
    try:
        import torch  # type: ignore
        # 从模型文件中读取统计数据
        checkpoint = torch.load(model_path, map_location='cpu')
        model_state = checkpoint['model_state_dict']
        
        # 从模型权重推断统计数据
        n_relations = model_state['relation_embed.weight'].shape[0]
        entity_user_embed_size = model_state['entity_user_embed.weight'].shape[0]
        
        logger.info(f"从模型文件读取: 关系数={n_relations}, 实体+用户总数={entity_user_embed_size}")
        
        # 获取数据库统计（用于获取用户数和商品数）
        data_adapter = DataAdapter(db)
        db_stats = data_adapter.get_statistics()
        
        # 使用模型文件中的统计数据
        # 注意：模型文件中的 entity_user_embed 包含实体+用户
        # 我们需要从数据库获取用户数，然后计算实体数
        n_users = db_stats['n_users']
        n_entities = entity_user_embed_size - n_users
        
        logger.info(f"计算得到: 用户数={n_users}, 实体数={n_entities}, 关系数={n_relations}")
        
        # 创建预测器（不加载模型，等待设置参数）
        predictor = KGATPredictor(model_path)
        
        # 创建模型（使用从模型文件推断的统计数据）
        try:
            predictor.create_model(
                n_users=n_users,
                n_entities=n_entities,
                n_relations=n_relations
            )
            predictor.n_items = db_stats['n_items']
        except Exception as e:
            logger.error(f"创建模型失败: {e}", exc_info=True)
            return None
        
        if not predictor.is_loaded():
            logger.error("模型加载失败")
            return None
        
        # 构建图
        # 获取交互和KG数据
        interactions = data_adapter.get_user_item_interactions()
        kg_triples = data_adapter.get_kg_triples()
        
        logger.info(f"加载了 {len(interactions)} 个交互和 {len(kg_triples)} 个KG三元组")
        
        # 构建图
        device = torch.device("cuda" if torch.cuda.is_available() and settings.USE_GPU else "cpu")
        graph = data_adapter.build_dgl_graph(
            interactions=interactions,
            kg_triples=kg_triples,
            n_users=n_users,
            n_entities=n_entities,
            device=device
        )
        
        predictor.graph = graph
        predictor.user_id_offset = n_entities
        
        logger.info("KGAT模型初始化完成")
        
        return predictor
        
    except Exception as e:
        logger.error(f"初始化KGAT模型失败: {e}", exc_info=True)
        return None
    finally:
        if should_close_db:
            db.close()


def reload_kgat_model(model_path: Optional[str] = None):
    """
    重新加载KGAT模型
    
    Args:
        model_path: 模型文件路径
    """
    db = SessionLocal()
    try:
        predictor = initialize_kgat_model(model_path, db)
        if predictor:
            reload_predictor(model_path)
            logger.info("KGAT模型重新加载成功")
        else:
            logger.error("KGAT模型重新加载失败")
    finally:
        db.close()


if __name__ == "__main__":
    # 测试模型加载
    logging.basicConfig(level=logging.INFO)
    
    model_path = settings.MODEL_PATH
    if not model_path:
        # 尝试使用默认路径
        model_path = "trained_model/KGAT/amazon-book/entitydim64_relationdim64_bi-interaction_64-32-16_lr0.0001_pretrain1/model_epoch1.pth"
    
    predictor = initialize_kgat_model(model_path)
    if predictor:
        print("模型加载成功！")
        print(f"用户数: {predictor.n_users}")
        print(f"商品数: {predictor.n_items}")
        print(f"实体数: {predictor.n_entities}")
    else:
        print("模型加载失败")


