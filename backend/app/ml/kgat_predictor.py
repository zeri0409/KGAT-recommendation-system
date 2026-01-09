"""
KGAT模型预测器
"""
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import torch
import dgl
import numpy as np

# 添加项目根目录到路径
# backend/app/ml/kgat_predictor.py -> 项目根目录
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 兼容本仓库目录结构：原始 KGAT 代码位于 <repo_root>/kgat/ 下，
# 其中包含 model/ 与 utility/ 两个包目录。
kgat_root = project_root / "kgat"
if kgat_root.exists() and str(kgat_root) not in sys.path:
    sys.path.insert(0, str(kgat_root))

from model.KGAT import KGAT
from utility.helper import load_model
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class KGATPredictor:
    """KGAT模型预测器"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化KGAT预测器
        
        Args:
            model_path: 模型文件路径，如果为None则从配置读取
        """
        self.model_path = model_path or settings.MODEL_PATH
        self.device = torch.device("cuda" if torch.cuda.is_available() and settings.USE_GPU else "cpu")
        self.model = None
        self.graph = None
        self.n_users = None
        self.n_items = None
        self.n_entities = None
        self.n_relations = None
        self.user_id_offset = None  # 用户ID在实体中的偏移量
        
        # 模型将在initialize_kgat_model中加载
        # 这里不自动加载，避免需要数据库连接
        if self.model_path and not os.path.exists(self.model_path):
            logger.warning(f"模型路径不存在: {self.model_path}，将使用轻量级推荐算法")
    
    def create_model(self, n_users: int, n_entities: int, n_relations: int):
        """
        创建KGAT模型（需要先设置参数）
        
        Args:
            n_users: 用户数量
            n_entities: 实体数量
            n_relations: 关系数量
        """
        if not self.model_path or not os.path.exists(self.model_path):
            raise ValueError(f"模型文件不存在: {self.model_path}")
        
        try:
            # 从模型路径推断配置
            path_parts = Path(self.model_path).parts
            config_str = path_parts[-2] if len(path_parts) > 1 else ""
            
            # 解析配置参数
            entity_dim = 64
            relation_dim = 64
            aggregation_type = "bi-interaction"
            conv_dim_list = "[64, 32, 16]"
            
            if "entitydim" in config_str:
                entity_dim = int(config_str.split("entitydim")[1].split("_")[0])
            if "relationdim" in config_str:
                relation_dim = int(config_str.split("relationdim")[1].split("_")[0])
            if "bi-interaction" in config_str:
                aggregation_type = "bi-interaction"
            elif "gcn" in config_str:
                aggregation_type = "gcn"
            elif "graphsage" in config_str:
                aggregation_type = "graphsage"
            
            # 创建args对象
            class Args:
                def __init__(self):
                    self.use_pretrain = 1
                    self.entity_dim = entity_dim
                    self.relation_dim = relation_dim
                    self.aggregation_type = aggregation_type
                    self.conv_dim_list = conv_dim_list
                    self.mess_dropout = "[0.1, 0.1, 0.1]"
                    self.kg_l2loss_lambda = 1e-5
                    self.cf_l2loss_lambda = 1e-5
            
            args = Args()
            
            # 设置参数
            self.n_users = n_users
            self.n_entities = n_entities
            self.n_relations = n_relations
            self.user_id_offset = n_entities
            
            # 创建模型
            self.model = KGAT(args, n_users, n_entities, n_relations)
            
            # 加载模型权重
            self.model = load_model(self.model, self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"KGAT模型创建并加载成功: {self.model_path}")
            logger.info(f"使用设备: {self.device}")
            logger.info(f"用户数: {n_users}, 实体数: {n_entities}, 关系数: {n_relations}")
            
        except Exception as e:
            logger.error(f"创建KGAT模型失败: {e}", exc_info=True)
            self.model = None
            raise
    
    def predict(self, user_ids: List[int], item_ids: List[int], graph=None) -> np.ndarray:
        """
        使用KGAT模型进行预测
        
        Args:
            user_ids: 用户ID列表
            item_ids: 商品ID列表
            graph: DGL图，如果为None则使用self.graph
        
        Returns:
            预测分数矩阵 (n_users, n_items)
        """
        if self.model is None:
            raise ValueError("模型未加载，无法进行预测")
        
        if graph is None:
            graph = self.graph
        
        if graph is None:
            raise ValueError("图未构建，无法进行预测")
        
        # 转换用户ID（加上偏移量）
        user_entity_ids = [uid + self.user_id_offset for uid in user_ids]
        
        # 转换为tensor
        user_tensor = torch.LongTensor(user_entity_ids).to(self.device)
        item_tensor = torch.LongTensor(item_ids).to(self.device)
        
        # 计算注意力分数
        with torch.no_grad():
            att = self.model.compute_attention(graph)
            graph.edata['att'] = att
            
            # 预测
            scores = self.model('predict', graph, user_tensor, item_tensor)
            scores = scores.cpu().numpy()
        
        return scores
    
    def get_recommendations(
        self,
        user_id: int,
        item_ids: List[int],
        top_k: int = 20,
        exclude_interacted: bool = True,
        interacted_items: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        获取用户推荐
        
        Args:
            user_id: 用户ID
            item_ids: 候选商品ID列表
            top_k: 返回top-k推荐
            exclude_interacted: 是否排除已交互的商品
            interacted_items: 已交互的商品ID列表
        
        Returns:
            推荐列表 [(item_id, score), ...]
        """
        if self.model is None:
            raise ValueError("模型未加载")
        
        if exclude_interacted and interacted_items:
            # 排除已交互的商品
            item_ids = [iid for iid in item_ids if iid not in interacted_items]
        
        if not item_ids:
            return []
        
        # 预测分数
        scores = self.predict([user_id], item_ids)
        scores = scores[0]  # 取第一个用户的分数
        
        # 获取top-k
        top_indices = np.argsort(scores)[::-1][:top_k]
        recommendations = [(item_ids[idx], float(scores[idx])) for idx in top_indices]
        
        return recommendations
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None


# 全局预测器实例（单例模式）
_predictor_instance: Optional[KGATPredictor] = None


def get_predictor() -> KGATPredictor:
    """获取全局预测器实例"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = KGATPredictor()
    return _predictor_instance


def reload_predictor(model_path: Optional[str] = None):
    """重新加载预测器"""
    global _predictor_instance
    _predictor_instance = KGATPredictor(model_path)

