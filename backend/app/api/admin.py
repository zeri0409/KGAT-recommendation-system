"""
管理员相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.api.deps import require_role
from app.models.user import User
from app.models.item import Item
from app.models.interaction import Interaction
from app.schemas.user import UserUpdate

router = APIRouter()


@router.get("/stats")
async def get_statistics(
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    获取系统统计信息（仅管理员）
    
    Args:
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        统计信息
    """
    # 用户统计
    total_users = db.query(func.count(User.user_id)).scalar()
    active_users = db.query(func.count(User.user_id)).filter(User.is_active == True).scalar()
    
    # 商品统计
    total_items = db.query(func.count(Item.item_id)).scalar()
    active_items = db.query(func.count(Item.item_id)).filter(Item.is_active == True).scalar()
    
    # 交互统计
    total_interactions = db.query(func.count(Interaction.interaction_id)).scalar()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users
        },
        "items": {
            "total": total_items,
            "active": active_items
        },
        "interactions": {
            "total": total_interactions
        }
    }


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    激活/停用用户（仅管理员）
    
    Args:
        user_id: 用户ID
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        更新后的用户信息
    
    Raises:
        HTTPException: 如果用户不存在
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return user


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db)
):
    """
    更新用户角色（仅超级管理员）
    
    Args:
        user_id: 用户ID
        new_role: 新角色
        current_user: 当前用户（超级管理员）
        db: 数据库会话
    
    Returns:
        更新后的用户信息
    
    Raises:
        HTTPException: 如果用户不存在或角色无效
    """
    if new_role not in ["user", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的角色"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    from app.models.user import UserRole
    user.role = UserRole(new_role)
    db.commit()
    db.refresh(user)
    
    return user


