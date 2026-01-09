"""
交互记录模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Interaction(Base):
    """用户-商品交互表"""
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False, index=True)  # view, click, purchase, rating, favorite
    rating = Column(Integer, CheckConstraint('rating >= 1 AND rating <= 5'), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    extra_metadata = Column(JSON, nullable=True)  # 存储额外信息，如浏览时长、设备类型等（metadata是SQLAlchemy保留字）

    # 关系
    user = relationship("User", back_populates="interactions")
    item = relationship("Item", back_populates="interactions")

    def __repr__(self):
        return f"<Interaction(interaction_id={self.interaction_id}, user_id={self.user_id}, item_id={self.item_id}, type={self.interaction_type})>"


