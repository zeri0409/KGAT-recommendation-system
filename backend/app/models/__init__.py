"""
数据库模型
"""
from app.models.user import User
from app.models.item import Item
from app.models.interaction import Interaction
from app.models.recommendation import Recommendation
from app.models.kg_triple import KGTriple
from app.models.cart import Cart
from app.models.order import Order, OrderDetail

__all__ = [
    "User",
    "Item",
    "Interaction",
    "Recommendation",
    "KGTriple",
    "Cart",
    "Order",
    "OrderDetail",
]
