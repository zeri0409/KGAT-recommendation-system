"""
知识图谱三元组模型
"""
from sqlalchemy import Column, Integer, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class KGTriple(Base):
    """知识图谱三元组表"""
    __tablename__ = "kg_triples"

    triple_id = Column(Integer, primary_key=True, index=True)
    head_entity_id = Column(Integer, nullable=False, index=True)
    relation_id = Column(Integer, nullable=False, index=True)
    tail_entity_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 唯一约束：相同的三元组只能存在一条
    __table_args__ = (
        UniqueConstraint('head_entity_id', 'relation_id', 'tail_entity_id', name='uq_kg_triple'),
    )

    def __repr__(self):
        return f"<KGTriple(head={self.head_entity_id}, relation={self.relation_id}, tail={self.tail_entity_id})>"


