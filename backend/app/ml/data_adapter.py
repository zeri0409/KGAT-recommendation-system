"""
数据适配器：从数据库加载数据并构建KGAT所需的数据结构

注意：
- 本文件被推荐服务在“非 KGAT 模式”下也会导入使用（用于读取交互/商品ID）。
- 为了让后端在未安装 torch/dgl 的情况下也能启动，torch/dgl 仅在需要构图时按需导入。
"""
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.interaction import Interaction
from app.models.kg_triple import KGTriple
from app.models.item import Item
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


class DataAdapter:
    """数据适配器：将数据库数据转换为KGAT所需格式"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_item_interactions(self) -> List[Tuple[int, int]]:
        """
        获取所有用户-商品交互
        
        Returns:
            交互列表 [(user_id, item_id), ...]
        """
        interactions = self.db.query(Interaction).all()
        return [(inter.user_id, inter.item_id) for inter in interactions]
    
    def get_kg_triples(self) -> List[Tuple[int, int, int]]:
        """
        获取所有知识图谱三元组
        
        Returns:
            三元组列表 [(head, relation, tail), ...]
        """
        triples = self.db.query(KGTriple).all()
        return [(t.head_entity_id, t.relation_id, t.tail_entity_id) for t in triples]
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取数据统计信息
        
        Returns:
            统计信息字典
        """
        n_users = self.db.query(User).count()
        n_items = self.db.query(Item).count()
        n_interactions = self.db.query(Interaction).count()
        n_kg_triples = self.db.query(KGTriple).count()
        
        # 获取最大实体ID（用于确定实体数量）
        max_head = self.db.query(func.max(KGTriple.head_entity_id)).scalar() or 0
        max_tail = self.db.query(func.max(KGTriple.tail_entity_id)).scalar() or 0
        max_entity_id = max(max_head, max_tail)
        
        # 获取最大关系ID
        max_relation_id = self.db.query(func.max(KGTriple.relation_id)).scalar() or 0
        
        return {
            'n_users': n_users,
            'n_items': n_items,
            'n_interactions': n_interactions,
            'n_kg_triples': n_kg_triples,
            'n_entities': max_entity_id + 1,
            'n_relations': max_relation_id + 1
        }
    
    def build_dgl_graph(
        self,
        interactions: List[Tuple[int, int]],
        kg_triples: List[Tuple[int, int, int]],
        n_users: int,
        n_entities: int,
        device: Optional[Any] = None
    ) -> Any:
        """
        构建DGL图
        
        Args:
            interactions: 用户-商品交互列表
            kg_triples: 知识图谱三元组列表
            n_users: 用户数量
            n_entities: 实体数量
            device: 设备（CPU/GPU）
        
        Returns:
            DGL图对象
        """
        # 按需导入：只有在真正使用 KGAT 构图时才需要 torch/dgl
        try:
            import dgl  # type: ignore
            import torch  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "构建 KGAT 图需要额外依赖：torch + dgl。"
                "如果你只是想跑后端 API，可在 .env 中设置 USE_KGAT_MODEL=False。"
            ) from e

        # 用户ID偏移量（用户ID在实体中的偏移）
        user_id_offset = n_entities
        
        # 构建边列表
        src_nodes = []
        dst_nodes = []
        edge_types = []
        
        # 添加用户-商品交互边（关系类型0和1）
        for user_id, item_id in interactions:
            user_entity_id = user_id + user_id_offset
            # 用户->商品（关系0）
            src_nodes.append(user_entity_id)
            dst_nodes.append(item_id)
            edge_types.append(0)
            # 商品->用户（关系1）
            src_nodes.append(item_id)
            dst_nodes.append(user_entity_id)
            edge_types.append(1)
        
        # 添加知识图谱边（关系类型从2开始）
        for head, relation, tail in kg_triples:
            src_nodes.append(head)
            dst_nodes.append(tail)
            edge_types.append(relation + 2)  # 关系ID从2开始（0和1被用户-商品关系占用）
        
        if not src_nodes:
            raise ValueError("没有边数据，无法构建图")
        
        # 计算节点总数
        n_nodes = n_users + n_entities
        
        # 创建图
        graph = dgl.graph((src_nodes, dst_nodes), num_nodes=n_nodes)
        graph.ndata['id'] = torch.arange(n_nodes, dtype=torch.long)
        graph.edata['type'] = torch.LongTensor(edge_types)
        
        # 移动到设备
        if device:
            graph = graph.to(device)
        
        logger.info(f"图构建成功: {graph.number_of_nodes()} 个节点, {graph.number_of_edges()} 条边")
        
        return graph
    
    def get_user_interacted_items(self, user_id: int) -> List[int]:
        """
        获取用户已交互的商品列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            商品ID列表
        """
        interactions = (
            self.db.query(Interaction.item_id)
            .filter(Interaction.user_id == user_id)
            .all()
        )
        return [inter[0] for inter in interactions]
    
    def get_all_item_ids(self) -> List[int]:
        """
        获取所有商品ID列表
        
        Returns:
            商品ID列表
        """
        items = self.db.query(Item.item_id).all()
        return [item[0] for item in items]

