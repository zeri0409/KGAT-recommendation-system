"""
交互服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate

class InteractionService:
    """交互服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_interaction(
        self,
        user_id: int,
        interaction_data: InteractionCreate
    ) -> Interaction:
        """创建交互记录"""
        db_interaction = Interaction(
            user_id=user_id,
            item_id=interaction_data.item_id,
            interaction_type=interaction_data.interaction_type,
            rating=interaction_data.rating,
            metadata=interaction_data.metadata
        )
        self.db.add(db_interaction)
        self.db.commit()
        self.db.refresh(db_interaction)
        return db_interaction
    
    def get_user_interactions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Interaction]:
        """获取用户的交互记录"""
        return (
            self.db.query(Interaction)
            .filter(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_item_interactions(
        self,
        item_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Interaction]:
        """获取商品的交互记录"""
        return (
            self.db.query(Interaction)
            .filter(Interaction.item_id == item_id)
            .order_by(Interaction.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


