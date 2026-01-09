"""
商品相关API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user, require_role
from app.models.user import User
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.services.item_service import ItemService

router = APIRouter()


@router.get("/", response_model=List[ItemResponse])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取商品列表
    
    Args:
        skip: 跳过数量
        limit: 返回数量
        category: 分类筛选
        search: 搜索关键词
        db: 数据库会话
    
    Returns:
        商品列表
    """
    service = ItemService(db)
    return service.list_items(skip=skip, limit=limit, category=category, search=search)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    获取商品详情
    
    Args:
        item_id: 商品ID
        db: 数据库会话
    
    Returns:
        商品信息
    
    Raises:
        HTTPException: 如果商品不存在
    """
    service = ItemService(db)
    item = service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    return item


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    创建商品（仅管理员）
    
    Args:
        item_data: 商品数据
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        创建的商品信息
    """
    service = ItemService(db)
    return service.create_item(item_data)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    更新商品（仅管理员）
    
    Args:
        item_id: 商品ID
        item_update: 商品更新数据
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Returns:
        更新后的商品信息
    
    Raises:
        HTTPException: 如果商品不存在
    """
    service = ItemService(db)
    item = service.update_item(item_id, item_update)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    db: Session = Depends(get_db)
):
    """
    删除商品（仅管理员）
    
    Args:
        item_id: 商品ID
        current_user: 当前用户（管理员）
        db: 数据库会话
    
    Raises:
        HTTPException: 如果商品不存在
    """
    service = ItemService(db)
    success = service.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )


