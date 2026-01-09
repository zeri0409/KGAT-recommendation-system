"""
交互记录相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class InteractionBase(BaseModel):
    """交互基础模型"""
    item_id: int
    interaction_type: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('interaction_type')
    @classmethod
    def validate_interaction_type(cls, v):
        allowed_types = ['view', 'click', 'purchase', 'rating', 'favorite', 'share']
        if v not in allowed_types:
            raise ValueError(f'interaction_type必须是以下之一: {allowed_types}')
        return v


class InteractionCreate(InteractionBase):
    """创建交互记录请求模型"""
    pass


class InteractionResponse(InteractionBase):
    """交互记录响应模型"""
    interaction_id: int
    user_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

