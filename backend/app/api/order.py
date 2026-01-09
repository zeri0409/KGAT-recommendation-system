"""
订单相关API
适配 vue-store 前端接口格式
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.services.order_service import OrderService

router = APIRouter()


# ==================== 请求/响应模型 ====================

class CreateOrderRequest(BaseModel):
    """创建订单请求 - 从购物车"""
    user_id: Optional[int] = None
    products: List[dict]  # [{"id": 购物车ID, "productID": 商品ID, "num": 数量}, ...]
    address: Optional[str] = None
    phone: Optional[str] = None
    receiver: Optional[str] = None
    remark: Optional[str] = None


class DirectOrderRequest(BaseModel):
    """直接购买请求"""
    product_id: int
    num: int = 1
    address: Optional[str] = None
    phone: Optional[str] = None
    receiver: Optional[str] = None
    remark: Optional[str] = None


class GetOrderRequest(BaseModel):
    """获取订单请求"""
    user_id: Optional[int] = None


class GetOrderDetailRequest(BaseModel):
    """获取订单详情请求"""
    order_id: int


class UpdateOrderStatusRequest(BaseModel):
    """更新订单状态请求"""
    order_id: int
    status: int


# ==================== 适配前端的接口 ====================

@router.post("/addOrder")
async def add_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建订单（从购物车）
    
    前端调用格式:
    POST /api/user/order/addOrder
    Body: {
        "user_id": 1,
        "products": [{"id": 1, "productID": 123, "num": 2}, ...],
        "address": "收货地址",
        "phone": "13800138000",
        "receiver": "张三"
    }
    
    响应格式:
    { "code": "001", "msg": "下单成功", "order": {...} }
    """
    service = OrderService(db)
    
    try:
        # 提取购物车ID列表
        cart_ids = [p.get("id") for p in request.products if p.get("id")]
        
        if not cart_ids:
            return {
                "code": "002",
                "msg": "请选择要购买的商品"
            }
        
        order = service.create_order_from_cart(
            user_id=current_user.user_id,
            cart_ids=cart_ids,
            address=request.address,
            phone=request.phone,
            receiver=request.receiver,
            remark=request.remark
        )
        
        return {
            "code": "001",
            "msg": "下单成功",
            "order": order.to_dict()
        }
    except ValueError as e:
        return {
            "code": "002",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"下单失败: {str(e)}"
        }


@router.post("/directOrder")
async def direct_order(
    request: DirectOrderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    直接购买（不经过购物车）
    
    前端调用格式:
    POST /api/user/order/directOrder
    Body: {
        "product_id": 123,
        "num": 1,
        "address": "收货地址"
    }
    """
    service = OrderService(db)
    
    try:
        order = service.create_order_direct(
            user_id=current_user.user_id,
            item_id=request.product_id,
            num=request.num,
            address=request.address,
            phone=request.phone,
            receiver=request.receiver,
            remark=request.remark
        )
        
        return {
            "code": "001",
            "msg": "下单成功",
            "order": order.to_dict()
        }
    except ValueError as e:
        return {
            "code": "002",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"下单失败: {str(e)}"
        }


@router.post("/getOrder")
async def get_order(
    request: GetOrderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户订单列表
    
    前端调用格式:
    POST /api/user/order/getOrder
    Body: { "user_id": 1 }
    
    响应格式:
    { "code": "001", "orders": [...] }
    """
    service = OrderService(db)
    
    try:
        orders = service.get_user_orders(current_user.user_id)
        
        return {
            "code": "001",
            "orders": [order.to_dict() for order in orders]
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"获取订单失败: {str(e)}"
        }


@router.post("/getOrderDetail")
async def get_order_detail(
    request: GetOrderDetailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取订单详情
    
    前端调用格式:
    POST /api/user/order/getOrderDetail
    Body: { "order_id": 1 }
    
    响应格式:
    { "code": "001", "order": {...} }
    """
    service = OrderService(db)
    
    try:
        order = service.get_order_detail(
            order_id=request.order_id,
            user_id=current_user.user_id
        )
        
        if order:
            return {
                "code": "001",
                "order": order.to_dict()
            }
        else:
            return {
                "code": "002",
                "msg": "订单不存在"
            }
    except PermissionError as e:
        return {
            "code": "003",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"获取订单详情失败: {str(e)}"
        }


@router.post("/cancelOrder")
async def cancel_order(
    request: GetOrderDetailRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    取消订单
    
    前端调用格式:
    POST /api/user/order/cancelOrder
    Body: { "order_id": 1 }
    
    响应格式:
    { "code": "001", "msg": "取消成功" }
    """
    service = OrderService(db)
    
    try:
        order = service.cancel_order(
            order_id=request.order_id,
            user_id=current_user.user_id
        )
        
        if order:
            return {
                "code": "001",
                "msg": "取消成功",
                "order": order.to_dict()
            }
        else:
            return {
                "code": "002",
                "msg": "订单不存在"
            }
    except PermissionError as e:
        return {
            "code": "003",
            "msg": str(e)
        }
    except ValueError as e:
        return {
            "code": "004",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"取消订单失败: {str(e)}"
        }


# ==================== RESTful 风格接口（可选） ====================

@router.get("/list")
async def list_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户订单列表（RESTful风格）"""
    service = OrderService(db)
    orders = service.get_user_orders(current_user.user_id)
    return {
        "code": "001",
        "data": [order.to_dict() for order in orders],
        "total": len(orders)
    }


@router.get("/{order_id}")
async def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取订单详情（RESTful风格）"""
    service = OrderService(db)
    
    try:
        order = service.get_order_detail(
            order_id=order_id,
            user_id=current_user.user_id
        )
        
        if order:
            return {
                "code": "001",
                "data": order.to_dict()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此订单"
        )


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: UpdateOrderStatusRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新订单状态（RESTful风格）"""
    service = OrderService(db)
    
    try:
        order = service.update_order_status(
            order_id=order_id,
            status=request.status,
            user_id=current_user.user_id
        )
        
        if order:
            return {
                "code": "001",
                "msg": "更新成功",
                "data": order.to_dict()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此订单"
        )
