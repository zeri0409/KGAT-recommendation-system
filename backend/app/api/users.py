"""
用户相关API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user, require_role
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前用户
    
    Returns:
        用户信息
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_info(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    Args:
        user_update: 用户更新数据
        current_user: 当前用户
        db: 数据库会话
    
    Returns:
        更新后的用户信息
    """
    service = UserService(db)
    return service.update_user(current_user.user_id, user_update)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    获取指定用户信息（仅管理员）
    
    Args:
        user_id: 用户ID
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        用户信息
    """
    service = UserService(db)
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（仅管理员）
    
    Args:
        skip: 跳过数量
        limit: 返回数量
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        用户列表
    """
    service = UserService(db)
    return service.list_users(skip=skip, limit=limit)


