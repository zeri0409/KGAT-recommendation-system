"""
购物车模型
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


def get_book_image_path(item_id: int) -> str:
    """生成本地图书封面路径（伪随机分配）"""
    hash_value = (item_id * 31 + item_id * 17 + 13) % 50
    image_index = hash_value + 1
    return f"/books/book_{image_index:02d}.jpg"


class Cart(Base):
    """购物车表"""
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False, index=True)
    num = Column(Integer, nullable=False, default=1)  # 商品数量
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 唯一约束：同一用户的同一商品只能有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', name='uq_user_item'),
    )

    # 关系
    user = relationship("User", backref="cart_items")
    item = relationship("Item", backref="cart_items")

    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, item_id={self.item_id}, num={self.num})>"

    def to_dict(self):
        """转换为前端期望的格式（下划线命名）"""
        # 使用本地图书封面图片
        image_url = get_book_image_path(self.item_id)
        
        product_name = ""
        product_price = 29.99
        
        if self.item:
            product_name = self.item.title or f"Book {self.item_id}"
            product_price = float(self.item.price) if self.item.price else 29.99
        
        return {
            # 前端购物车组件期望的字段（下划线命名）
            "id": self.id,
            "product_id": self.item_id,
            "product_name": product_name,
            "product_picture": image_url,
            "product_price": product_price,
            "product_num": self.num,
            "max_num": 10,  # 限购数量
            "check": False,  # 前端勾选状态，默认未勾选
            
            # 兼容驼峰命名（某些前端组件可能使用）
            "productID": self.item_id,
            "productName": product_name,
            "productImg": image_url,
            "price": product_price,
            "num": self.num,
            "maxNum": 10,
        }
