"""
商品服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate

class ItemService:
    """商品服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """根据ID获取商品"""
        return self.db.query(Item).filter(Item.item_id == item_id).first()
    
    def list_items(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Item]:
        """获取商品列表"""
        query = self.db.query(Item).filter(Item.is_active == True)
        
        if category:
            query = query.filter(Item.category == category)
        
        if search:
            query = query.filter(
                or_(
                    Item.title.ilike(f"%{search}%"),
                    Item.description.ilike(f"%{search}%")
                )
            )
        
        return query.offset(skip).limit(limit).all()
    
    def create_item(self, item_data: ItemCreate) -> Item:
        """创建商品"""
        db_item = Item(**item_data.dict())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def update_item(self, item_id: int, item_update: ItemUpdate) -> Optional[Item]:
        """更新商品"""
        item = self.get_item_by_id(item_id)
        if not item:
            return None
        
        update_data = item_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def delete_item(self, item_id: int) -> bool:
        """删除商品（软删除）"""
        item = self.get_item_by_id(item_id)
        if not item:
            return False
        
        item.is_active = False
        self.db.commit()
        return True


