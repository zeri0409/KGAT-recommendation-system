"""
订单模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True)  # 订单号
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    total_price = Column(Numeric(10, 2), nullable=False, default=0)  # 订单总价
    status = Column(Integer, nullable=False, default=0)  # 订单状态: 0-待付款, 1-已付款, 2-已发货, 3-已完成, 4-已取消
    address = Column(Text, nullable=True)  # 收货地址
    phone = Column(String(20), nullable=True)  # 联系电话
    receiver = Column(String(50), nullable=True)  # 收货人
    remark = Column(Text, nullable=True)  # 订单备注
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", backref="orders")
    details = relationship("OrderDetail", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, order_no={self.order_no}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "orderNo": self.order_no,
            "userId": self.user_id,
            "totalPrice": float(self.total_price) if self.total_price else 0,
            "status": self.status,
            "statusText": self.get_status_text(),
            "address": self.address,
            "phone": self.phone,
            "receiver": self.receiver,
            "remark": self.remark,
            "createTime": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "products": [detail.to_dict() for detail in self.details] if self.details else []
        }

    def get_status_text(self):
        """获取状态文本"""
        status_map = {
            0: "待付款",
            1: "已付款",
            2: "已发货",
            3: "已完成",
            4: "已取消"
        }
        return status_map.get(self.status, "未知")


class OrderDetail(Base):
    """订单详情表"""
    __tablename__ = "order_details"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.item_id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String(255), nullable=False)  # 商品名称（冗余存储，防止商品删除后丢失）
    product_img = Column(String(500), nullable=True)  # 商品图片
    price = Column(Numeric(10, 2), nullable=False)  # 商品单价
    num = Column(Integer, nullable=False, default=1)  # 购买数量
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    order = relationship("Order", back_populates="details")
    item = relationship("Item", backref="order_details")

    def __repr__(self):
        return f"<OrderDetail(id={self.id}, order_id={self.order_id}, item_id={self.item_id}, num={self.num})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "orderId": self.order_id,
            "productID": self.item_id,
            "productName": self.product_name,
            "productImg": self.product_img,
            "price": float(self.price) if self.price else 0,
            "num": self.num,
            "totalPrice": float(self.price * self.num) if self.price else 0
        }
