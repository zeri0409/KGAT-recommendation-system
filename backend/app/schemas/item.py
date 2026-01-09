"""
商品相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ItemBase(BaseModel):
    """商品基础模型"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)


class ItemCreate(ItemBase):
    """创建商品请求模型"""
    pass


class ItemUpdate(BaseModel):
    """更新商品请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    is_active: Optional[bool] = None


class ItemResponse(ItemBase):
    """商品响应模型"""
    item_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


