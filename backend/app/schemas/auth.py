"""
认证相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据模型"""
    username: Optional[str] = None
    user_id: Optional[int] = None


