"""
购物车服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.cart import Cart
from app.models.item import Item


class CartService:
    """购物车服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_cart_by_id(self, cart_id: int) -> Optional[Cart]:
        """根据ID获取购物车记录"""
        return self.db.query(Cart).filter(Cart.id == cart_id).first()
    
    def get_cart_item(self, user_id: int, item_id: int) -> Optional[Cart]:
        """获取用户购物车中的指定商品"""
        return self.db.query(Cart).filter(
            Cart.user_id == user_id,
            Cart.item_id == item_id
        ).first()
    
    def get_user_cart(self, user_id: int) -> List[Cart]:
        """获取用户的购物车列表"""
        return self.db.query(Cart).filter(Cart.user_id == user_id).all()
    
    def add_to_cart(self, user_id: int, item_id: int, num: int = 1) -> Cart:
        """
        添加商品到购物车
        如果商品已存在，则增加数量
        """
        # 检查商品是否存在
        item = self.db.query(Item).filter(Item.item_id == item_id).first()
        if not item:
            raise ValueError(f"商品不存在: {item_id}")
        
        # 检查购物车中是否已有该商品
        cart_item = self.get_cart_item(user_id, item_id)
        
        if cart_item:
            # 已存在，增加数量
            cart_item.num += num
            self.db.commit()
            self.db.refresh(cart_item)
            return cart_item
        else:
            # 不存在，新增记录
            cart_item = Cart(
                user_id=user_id,
                item_id=item_id,
                num=num
            )
            self.db.add(cart_item)
            self.db.commit()
            self.db.refresh(cart_item)
            return cart_item
    
    def update_cart_num(self, cart_id: int, num: int, user_id: int = None) -> Optional[Cart]:
        """
        更新购物车商品数量
        
        Args:
            cart_id: 购物车记录ID
            num: 新数量
            user_id: 用户ID（用于验证权限）
        """
        cart_item = self.get_cart_by_id(cart_id)
        
        if not cart_item:
            return None
        
        # 验证是否是该用户的购物车
        if user_id and cart_item.user_id != user_id:
            raise PermissionError("无权操作此购物车")
        
        if num <= 0:
            # 数量为0或负数，删除该记录
            self.db.delete(cart_item)
            self.db.commit()
            return None
        
        cart_item.num = num
        self.db.commit()
        self.db.refresh(cart_item)
        return cart_item
    
    def delete_cart_item(self, cart_id: int, user_id: int = None) -> bool:
        """
        删除购物车商品
        
        Args:
            cart_id: 购物车记录ID
            user_id: 用户ID（用于验证权限）
        
        Returns:
            是否删除成功
        """
        cart_item = self.get_cart_by_id(cart_id)
        
        if not cart_item:
            return False
        
        # 验证是否是该用户的购物车
        if user_id and cart_item.user_id != user_id:
            raise PermissionError("无权操作此购物车")
        
        self.db.delete(cart_item)
        self.db.commit()
        return True
    
    def delete_cart_by_item(self, user_id: int, item_id: int) -> bool:
        """
        根据用户ID和商品ID删除购物车记录
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
        
        Returns:
            是否删除成功
        """
        cart_item = self.get_cart_item(user_id, item_id)
        
        if not cart_item:
            return False
        
        self.db.delete(cart_item)
        self.db.commit()
        return True
    
    def clear_cart(self, user_id: int) -> int:
        """
        清空用户购物车
        
        Args:
            user_id: 用户ID
        
        Returns:
            删除的记录数
        """
        deleted = self.db.query(Cart).filter(Cart.user_id == user_id).delete()
        self.db.commit()
        return deleted
    
    def get_cart_count(self, user_id: int) -> int:
        """获取用户购物车商品种类数量"""
        return self.db.query(Cart).filter(Cart.user_id == user_id).count()
    
    def get_cart_total_num(self, user_id: int) -> int:
        """获取用户购物车商品总数量"""
        from sqlalchemy import func
        result = self.db.query(func.sum(Cart.num)).filter(Cart.user_id == user_id).scalar()
        return result or 0
