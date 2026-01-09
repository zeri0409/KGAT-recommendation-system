"""
商品模型
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    """商品表"""
    __tablename__ = "items"

    item_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Numeric(10, 2), nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    interactions = relationship("Interaction", back_populates="item", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(item_id={self.item_id}, title={self.title})>"


