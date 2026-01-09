"""
推荐结果模型
"""
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Recommendation(Base):
    """推荐结果表"""
    __tablename__ = "recommendations"

    recommendation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Numeric(10, 6), nullable=False)  # 推荐分数
    rank = Column(Integer, nullable=False)  # 排名
    model_version = Column(String(50), nullable=True)  # 模型版本
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 关系
    user = relationship("User", back_populates="recommendations")
    item = relationship("Item", back_populates="recommendations")

    # 唯一约束：同一用户同一商品同一模型版本只能有一条推荐记录
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', 'model_version', name='uq_user_item_model'),
    )

    def __repr__(self):
        return f"<Recommendation(user_id={self.user_id}, item_id={self.item_id}, score={self.score}, rank={self.rank})>"


