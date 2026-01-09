"""
购物车相关API
适配 vue-store 前端接口格式
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.services.cart_service import CartService

router = APIRouter()


# ==================== 请求/响应模型 ====================

class GetCartRequest(BaseModel):
    """获取购物车请求"""
    user_id: Optional[int] = None


class AddCartRequest(BaseModel):
    """添加购物车请求"""
    user_id: Optional[int] = None
    product_id: int
    num: int = 1


class UpdateCartRequest(BaseModel):
    """更新购物车请求"""
    id: int
    num: int


class DeleteCartRequest(BaseModel):
    """删除购物车请求 - 支持两种方式"""
    id: Optional[int] = None  # 购物车记录ID
    user_id: Optional[int] = None
    product_id: Optional[int] = None  # 商品ID


# ==================== 适配前端的接口 ====================

@router.post("/getShoppingCart")
async def get_shopping_cart(
    request: GetCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取购物车列表
    
    前端调用格式:
    POST /api/user/shoppingCart/getShoppingCart
    Body: { "user_id": 1 }
    
    响应格式:
    { "code": "001", "shoppingCartData": [...] }
    """
    service = CartService(db)
    cart_items = service.get_user_cart(current_user.user_id)
    
    # 转换为前端期望的格式
    shopping_cart_data = [item.to_dict() for item in cart_items]
    
    return {
        "code": "001",
        "shoppingCartData": shopping_cart_data
    }


@router.post("/addShoppingCart")
async def add_shopping_cart(
    request: AddCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    添加商品到购物车
    
    前端调用格式:
    POST /api/user/shoppingCart/addShoppingCart
    Body: { "user_id": 1, "product_id": 123, "num": 1 }
    
    响应格式:
    - 新添加: { "code": "001", "msg": "添加成功", "shoppingCartData": [...] }
    - 已存在数量+1: { "code": "002", "msg": "该商品已在购物车，数量+1" }
    - 达到限购: { "code": "003", "msg": "商品限购10件" }
    """
    service = CartService(db)
    
    try:
        # 检查商品是否已在购物车
        existing_item = service.get_cart_item(
            user_id=current_user.user_id,
            item_id=request.product_id
        )
        
        if existing_item:
            # 商品已存在，数量+1
            current_num = existing_item.num
            max_num = 10  # 限购数量
            
            if current_num >= max_num:
                return {
                    "code": "003",
                    "msg": f"该商品限购{max_num}件"
                }
            
            # 更新数量
            updated_item = service.update_cart_num(
                cart_id=existing_item.id,
                num=current_num + 1,
                user_id=current_user.user_id
            )
            
            return {
                "code": "002",
                "msg": "该商品已在购物车，数量+1"
            }
        else:
            # 新商品，添加到购物车
            cart_item = service.add_to_cart(
                user_id=current_user.user_id,
                item_id=request.product_id,
                num=request.num
            )
            
            return {
                "code": "001",
                "msg": "添加购物车成功",
                "shoppingCartData": [cart_item.to_dict()]
            }
            
    except ValueError as e:
        return {
            "code": "004",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"添加失败: {str(e)}"
        }


@router.post("/updateShoppingCart")
async def update_shopping_cart(
    request: UpdateCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新购物车商品数量
    
    前端调用格式:
    POST /api/user/shoppingCart/updateShoppingCart
    Body: { "id": 1, "num": 2 }
    
    响应格式:
    { "code": "001", "msg": "更新成功" }
    """
    service = CartService(db)
    
    try:
        cart_item = service.update_cart_num(
            cart_id=request.id,
            num=request.num,
            user_id=current_user.user_id
        )
        
        if request.num <= 0:
            return {
                "code": "001",
                "msg": "商品已从购物车删除"
            }
        
        if cart_item:
            return {
                "code": "001",
                "msg": "更新成功",
                "data": cart_item.to_dict()
            }
        else:
            return {
                "code": "002",
                "msg": "购物车记录不存在"
            }
    except PermissionError as e:
        return {
            "code": "003",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"更新失败: {str(e)}"
        }


@router.post("/deleteShoppingCart")
async def delete_shopping_cart(
    request: DeleteCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除购物车商品
    
    前端调用格式:
    POST /api/user/shoppingCart/deleteShoppingCart
    Body: { "id": 1 } 或 { "user_id": 1, "product_id": 123 }
    
    响应格式:
    { "code": "001", "msg": "删除成功" }
    """
    service = CartService(db)
    
    try:
        success = False
        
        if request.id:
            # 通过购物车记录ID删除
            success = service.delete_cart_item(
                cart_id=request.id,
                user_id=current_user.user_id
            )
        elif request.product_id:
            # 通过商品ID删除
            success = service.delete_cart_by_item(
                user_id=current_user.user_id,
                item_id=request.product_id
            )
        
        if success:
            return {
                "code": "001",
                "msg": "删除成功"
            }
        else:
            return {
                "code": "002",
                "msg": "购物车记录不存在"
            }
    except PermissionError as e:
        return {
            "code": "003",
            "msg": str(e)
        }
    except Exception as e:
        return {
            "code": "500",
            "msg": f"删除失败: {str(e)}"
        }


# ==================== RESTful 风格接口（可选） ====================

@router.get("/list")
async def list_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户购物车列表（RESTful风格）"""
    service = CartService(db)
    cart_items = service.get_user_cart(current_user.user_id)
    return {
        "code": "001",
        "data": [item.to_dict() for item in cart_items],
        "total": len(cart_items)
    }


@router.post("/clear")
async def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """清空购物车"""
    service = CartService(db)
    deleted_count = service.clear_cart(current_user.user_id)
    return {
        "code": "001",
        "msg": f"已清空购物车，删除了 {deleted_count} 件商品"
    }


@router.get("/count")
async def cart_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取购物车商品数量"""
    service = CartService(db)
    count = service.get_cart_count(current_user.user_id)
    total_num = service.get_cart_total_num(current_user.user_id)
    return {
        "code": "001",
        "count": count,  # 商品种类数
        "totalNum": total_num  # 商品总数量
    }
