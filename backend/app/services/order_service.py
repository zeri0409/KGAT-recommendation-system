"""
订单服务
"""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.order import Order, OrderDetail
from app.models.cart import Cart
from app.models.item import Item


class OrderService:
    """订单服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_order_no(self) -> str:
        """生成订单号"""
        import time
        timestamp = int(time.time() * 1000)
        random_str = uuid.uuid4().hex[:8].upper()
        return f"ORD{timestamp}{random_str}"
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """根据ID获取订单"""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_order_by_no(self, order_no: str) -> Optional[Order]:
        """根据订单号获取订单"""
        return self.db.query(Order).filter(Order.order_no == order_no).first()
    
    def get_user_orders(self, user_id: int) -> List[Order]:
        """获取用户的所有订单"""
        return self.db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(Order.created_at.desc()).all()
    
    def create_order_from_cart(
        self,
        user_id: int,
        cart_ids: List[int],
        address: str = None,
        phone: str = None,
        receiver: str = None,
        remark: str = None
    ) -> Order:
        """
        从购物车创建订单
        
        Args:
            user_id: 用户ID
            cart_ids: 购物车记录ID列表
            address: 收货地址
            phone: 联系电话
            receiver: 收货人
            remark: 备注
        
        Returns:
            创建的订单
        """
        # 获取购物车商品
        cart_items = self.db.query(Cart).filter(
            Cart.id.in_(cart_ids),
            Cart.user_id == user_id
        ).all()
        
        if not cart_items:
            raise ValueError("购物车中没有选中的商品")
        
        # 计算总价
        total_price = 0
        order_details = []
        
        for cart_item in cart_items:
            item = cart_item.item
            if not item:
                continue
            
            price = float(item.price) if item.price else 0
            total_price += price * cart_item.num
            
            order_details.append({
                "item_id": item.item_id,
                "product_name": item.title or f"商品{item.item_id}",
                "product_img": item.image_url,
                "price": price,
                "num": cart_item.num
            })
        
        # 创建订单
        order = Order(
            order_no=self.generate_order_no(),
            user_id=user_id,
            total_price=total_price,
            status=0,  # 待付款
            address=address,
            phone=phone,
            receiver=receiver,
            remark=remark
        )
        self.db.add(order)
        self.db.flush()  # 获取order.id
        
        # 创建订单详情
        for detail_data in order_details:
            detail = OrderDetail(
                order_id=order.id,
                item_id=detail_data["item_id"],
                product_name=detail_data["product_name"],
                product_img=detail_data["product_img"],
                price=detail_data["price"],
                num=detail_data["num"]
            )
            self.db.add(detail)
        
        # 清空已下单的购物车商品
        for cart_item in cart_items:
            self.db.delete(cart_item)
        
        self.db.commit()
        self.db.refresh(order)
        
        return order
    
    def create_order_direct(
        self,
        user_id: int,
        item_id: int,
        num: int = 1,
        address: str = None,
        phone: str = None,
        receiver: str = None,
        remark: str = None
    ) -> Order:
        """
        直接购买创建订单（不经过购物车）
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            num: 购买数量
            address: 收货地址
            phone: 联系电话
            receiver: 收货人
            remark: 备注
        
        Returns:
            创建的订单
        """
        # 获取商品信息
        item = self.db.query(Item).filter(Item.item_id == item_id).first()
        if not item:
            raise ValueError(f"商品不存在: {item_id}")
        
        price = float(item.price) if item.price else 0
        total_price = price * num
        
        # 创建订单
        order = Order(
            order_no=self.generate_order_no(),
            user_id=user_id,
            total_price=total_price,
            status=0,
            address=address,
            phone=phone,
            receiver=receiver,
            remark=remark
        )
        self.db.add(order)
        self.db.flush()
        
        # 创建订单详情
        detail = OrderDetail(
            order_id=order.id,
            item_id=item.item_id,
            product_name=item.title or f"商品{item.item_id}",
            product_img=item.image_url,
            price=price,
            num=num
        )
        self.db.add(detail)
        
        self.db.commit()
        self.db.refresh(order)
        
        return order
    
    def update_order_status(self, order_id: int, status: int, user_id: int = None) -> Optional[Order]:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            status: 新状态
            user_id: 用户ID（用于验证权限）
        
        Returns:
            更新后的订单
        """
        order = self.get_order_by_id(order_id)
        
        if not order:
            return None
        
        if user_id and order.user_id != user_id:
            raise PermissionError("无权操作此订单")
        
        order.status = status
        self.db.commit()
        self.db.refresh(order)
        
        return order
    
    def cancel_order(self, order_id: int, user_id: int = None) -> Optional[Order]:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            user_id: 用户ID（用于验证权限）
        
        Returns:
            取消后的订单
        """
        order = self.get_order_by_id(order_id)
        
        if not order:
            return None
        
        if user_id and order.user_id != user_id:
            raise PermissionError("无权操作此订单")
        
        # 只有待付款和已付款状态可以取消
        if order.status not in [0, 1]:
            raise ValueError("当前订单状态不可取消")
        
        order.status = 4  # 已取消
        self.db.commit()
        self.db.refresh(order)
        
        return order
    
    def get_order_detail(self, order_id: int, user_id: int = None) -> Optional[Order]:
        """
        获取订单详情
        
        Args:
            order_id: 订单ID
            user_id: 用户ID（用于验证权限）
        
        Returns:
            订单详情
        """
        order = self.get_order_by_id(order_id)
        
        if not order:
            return None
        
        if user_id and order.user_id != user_id:
            raise PermissionError("无权查看此订单")
        
        return order
