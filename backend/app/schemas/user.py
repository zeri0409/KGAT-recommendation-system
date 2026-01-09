"""
用户相关的Pydantic模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """创建用户请求模型"""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class UserLogin(BaseModel):
    """用户登录请求模型"""
    username: str
    password: str


class UserResponse(UserBase):
    """用户响应模型"""
    user_id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型（包含密码哈希）"""
    password_hash: str


