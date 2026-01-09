"""
推荐相关API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user, require_role
from app.models.user import User
from app.models.item import Item
from app.schemas.recommendation import RecommendationResponse
from app.schemas.interaction import InteractionCreate
from app.services.recommendation_service import RecommendationService
from app.services.interaction_service import InteractionService

router = APIRouter()


def get_book_image_path(item_id: int) -> str:
    """生成本地图书封面路径（伪随机分配）"""
    hash_value = (item_id * 31 + item_id * 17 + 13) % 50
    image_index = hash_value + 1
    return f"/books/book_{image_index:02d}.jpg"


# 固定的热门商品ID列表（可以根据实际情况修改）
HOT_PRODUCT_IDS = [134, 25, 610, 157, 2, 825, 301, 395, 504, 1007, 1508, 2080, 300, 6509, 8, 13]


@router.get("/popular")
async def get_popular_products(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取热门商品列表（无需登录）
    
    Args:
        limit: 返回数量，默认8
        db: 数据库会话
    
    Returns:
        热门商品列表
    """
    # 方法1：使用固定的热门商品ID
    hot_items = []
    
    for item_id in HOT_PRODUCT_IDS[:limit]:
        item = db.query(Item).filter(
            Item.item_id == item_id,
            Item.is_active == True
        ).first()
        
        if item:
            hot_items.append({
                "item_id": item.item_id,
                "title": item.title or f"Book {item.item_id}",
                "description": item.description,
                "price": float(item.price) if item.price else 29.99,
                "rating": float(item.rating) if item.rating else 4.5,
                "image_url": get_book_image_path(item.item_id),
                "category": item.category
            })
    
    # 如果固定ID的商品不够，从数据库补充
    if len(hot_items) < limit:
        existing_ids = [item["item_id"] for item in hot_items]
        additional_items = db.query(Item).filter(
            Item.is_active == True,
            ~Item.item_id.in_(existing_ids)
        ).order_by(
            Item.rating.desc().nulls_last()
        ).limit(limit - len(hot_items)).all()
        
        for item in additional_items:
            hot_items.append({
                "item_id": item.item_id,
                "title": item.title or f"Book {item.item_id}",
                "description": item.description,
                "price": float(item.price) if item.price else 29.99,
                "rating": float(item.rating) if item.rating else 4.5,
                "image_url": get_book_image_path(item.item_id),
                "category": item.category
            })
    
    return {
        "recommendations": hot_items,
        "count": len(hot_items)
    }


@router.get("/me", response_model=RecommendationResponse)
async def get_my_recommendations(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的推荐列表
    
    Args:
        limit: 返回推荐数量
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        推荐结果
    """
    service = RecommendationService(db)
    recommendations = service.get_recommendations(current_user.user_id, limit=limit)
    
    return {
        "user_id": current_user.user_id,
        "recommendations": recommendations,
        "count": len(recommendations)
    }


@router.get("/{user_id}", response_model=RecommendationResponse)
async def get_user_recommendations(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定用户的推荐列表
    
    - 用户只能查看自己的推荐
    - 管理员可以查看任何用户的推荐
    
    Args:
        user_id: 用户ID
        limit: 返回推荐数量
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        推荐结果
    
    Raises:
        HTTPException: 如果无权访问
    """
    if current_user.user_id != user_id and current_user.role.value not in ['admin', 'super_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他用户的推荐"
        )
    
    service = RecommendationService(db)
    recommendations = service.get_recommendations(user_id, limit=limit)
    
    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "count": len(recommendations)
    }


@router.post("/record-interaction")
async def record_interaction(
    interaction_data: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    记录用户交互
    
    Args:
        interaction_data: 交互数据
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        交互记录ID
    """
    interaction_service = InteractionService(db)
    recommendation_service = RecommendationService(db)
    
    # 创建交互记录
    interaction = interaction_service.create_interaction(
        user_id=current_user.user_id,
        interaction_data=interaction_data
    )
    
    # 如果达到阈值，触发推荐更新
    if recommendation_service.should_update_recommendations(current_user.user_id):
        # 异步更新推荐（这里简化处理，实际应该用Celery）
        recommendation_service.update_recommendations_realtime(current_user.user_id)
    
    return {
        "message": "交互记录成功",
        "interaction_id": interaction.interaction_id
    }
