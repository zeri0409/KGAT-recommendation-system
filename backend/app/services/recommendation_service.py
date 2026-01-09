"""
推荐服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.recommendation import Recommendation
from app.models.interaction import Interaction
from app.config import settings
from app.ml.data_adapter import DataAdapter
import redis
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()
except:
    redis_client = None  # Redis不可用时继续运行


class RecommendationService:
    """推荐服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.data_adapter = DataAdapter(db)
        self.predictor = None
        if settings.USE_KGAT_MODEL:
            try:
                # 按需导入：未启用 KGAT 时不要强依赖 torch/dgl
                from app.ml.kgat_predictor import get_predictor
                self.predictor = get_predictor()
            except Exception as e:
                logger.warning(f"KGAT模型加载失败，将使用轻量级算法: {e}")
                self.predictor = None
    
    def get_recommendations(
        self,
        user_id: int,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[dict]:
        """
        获取用户推荐
        
        Args:
            user_id: 用户ID
            limit: 返回推荐数量
            use_cache: 是否使用缓存
        
        Returns:
            推荐商品列表
        """
        # 尝试从缓存获取
        if use_cache and redis_client:
            try:
                cached = redis_client.get(f'recommendations:{user_id}')
                if cached:
                    return json.loads(cached)
            except:
                pass
        
        # 从数据库获取推荐
        recommendations = (
            self.db.query(Recommendation)
            .filter(Recommendation.user_id == user_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        
        if recommendations:
            result = [
                {
                    'item_id': rec.item_id,
                    'score': float(rec.score),
                    'rank': rec.rank
                }
                for rec in recommendations
            ]
            # 缓存
            if redis_client:
                try:
                    redis_client.setex(
                        f'recommendations:{user_id}',
                        settings.RECOMMENDATION_CACHE_TTL,
                        json.dumps(result)
                    )
                except:
                    pass
            return result
        
        # 如果数据库没有，实时计算
        if self.predictor and self.predictor.is_loaded():
            return self.compute_recommendations_kgat(user_id, limit)
        else:
            return self.compute_recommendations_realtime(user_id, limit)
    
    def compute_recommendations_realtime(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[dict]:
        """
        实时计算推荐（基于最近交互的轻量级算法）
        """
        # 获取用户最近交互
        recent_interactions = (
            self.db.query(Interaction)
            .filter(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.desc())
            .limit(50)
            .all()
        )
        
        if not recent_interactions:
            # 新用户，返回热门商品
            return self.get_popular_items(limit)
        
        # 基于ItemCF计算相似商品
        recent_item_ids = [inter.item_id for inter in recent_interactions]
        similar_items = self.compute_item_similarity(recent_item_ids, limit)
        
        return similar_items
    
    def compute_item_similarity(
        self,
        item_ids: List[int],
        limit: int
    ) -> List[dict]:
        """
        基于ItemCF计算相似商品
        """
        # 获取与这些商品交互过的其他用户
        other_users = (
            self.db.query(Interaction.user_id)
            .filter(Interaction.item_id.in_(item_ids))
            .distinct()
            .all()
        )
        
        if not other_users:
            return self.get_popular_items(limit)
        
        user_ids = [u[0] for u in other_users]
        
        # 获取这些用户交互的其他商品
        similar_items = (
            self.db.query(
                Interaction.item_id,
                func.count(Interaction.item_id).label('count')
            )
            .filter(
                Interaction.user_id.in_(user_ids),
                ~Interaction.item_id.in_(item_ids)  # 排除已交互的商品
            )
            .group_by(Interaction.item_id)
            .order_by(func.count(Interaction.item_id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                'item_id': item_id,
                'score': float(count),
                'rank': idx + 1
            }
            for idx, (item_id, count) in enumerate(similar_items)
        ]
    
    def get_popular_items(self, limit: int) -> List[dict]:
        """获取热门商品"""
        popular = (
            self.db.query(
                Interaction.item_id,
                func.count(Interaction.item_id).label('count')
            )
            .group_by(Interaction.item_id)
            .order_by(func.count(Interaction.item_id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                'item_id': item_id,
                'score': float(count),
                'rank': idx + 1
            }
            for idx, (item_id, count) in enumerate(popular)
        ]
    
    def should_update_recommendations(self, user_id: int) -> bool:
        """
        判断是否需要更新推荐
        """
        if not redis_client:
            return True
        
        try:
            last_update = redis_client.get(f'last_update:{user_id}')
            if not last_update:
                return True
            
            # 如果距离上次更新超过1小时，需要更新
            last_update_time = datetime.fromisoformat(last_update)
            return datetime.now() - last_update_time > timedelta(hours=1)
        except:
            return True
    
    def compute_recommendations_kgat(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[dict]:
        """
        使用KGAT模型计算推荐
        
        Args:
            user_id: 用户ID
            limit: 返回推荐数量
        
        Returns:
            推荐商品列表
        """
        if not self.predictor or not self.predictor.is_loaded():
            logger.warning("KGAT模型未加载，回退到轻量级算法")
            return self.compute_recommendations_realtime(user_id, limit)
        
        try:
            # 获取用户已交互的商品
            interacted_items = self.data_adapter.get_user_interacted_items(user_id)
            
            # 获取所有商品ID
            all_item_ids = self.data_adapter.get_all_item_ids()
            
            # 使用KGAT模型预测
            recommendations = self.predictor.get_recommendations(
                user_id=user_id,
                item_ids=all_item_ids,
                top_k=limit,
                exclude_interacted=True,
                interacted_items=interacted_items
            )
            
            # 转换为标准格式
            result = [
                {
                    'item_id': item_id,
                    'score': score,
                    'rank': idx + 1
                }
                for idx, (item_id, score) in enumerate(recommendations)
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"KGAT推荐计算失败: {e}", exc_info=True)
            # 回退到轻量级算法
            return self.compute_recommendations_realtime(user_id, limit)
    
    def update_recommendations_realtime(self, user_id: int):
        """
        实时更新推荐（简化版）
        """
        if self.predictor and self.predictor.is_loaded():
            recommendations = self.compute_recommendations_kgat(user_id)
        else:
            recommendations = self.compute_recommendations_realtime(user_id)
        
        # 更新缓存
        if redis_client:
            try:
                redis_client.setex(
                    f'recommendations:{user_id}',
                    settings.RECOMMENDATION_CACHE_TTL,
                    json.dumps(recommendations)
                )
                redis_client.set(
                    f'last_update:{user_id}',
                    datetime.now().isoformat()
                )
            except:
                pass

