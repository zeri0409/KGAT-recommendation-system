"""
推荐结果相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import List
from decimal import Decimal


class RecommendationItem(BaseModel):
    """单个推荐项"""
    item_id: int
    score: Decimal
    rank: int


class RecommendationResponse(BaseModel):
    """推荐结果响应模型"""
    user_id: int
    recommendations: List[RecommendationItem]
    count: int


