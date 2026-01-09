"""
商品接口适配层 - 兼容前端旧接口
将前端的旧接口格式映射到新的RESTful接口
"""
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.item_service import ItemService
from app.schemas.item import ItemResponse
from pydantic import BaseModel

router = APIRouter()


# ========== 图片路径生成函数 ==========
def get_book_image_path(item_id: int) -> str:
    """生成本地图书封面路径（伪随机分配，同一商品始终显示同一图片）"""
    # 使用简单哈希函数打乱图片顺序，避免尾号相同的商品显示相同图片
    hash_value = (item_id * 31 + item_id * 17 + 13) % 50
    image_index = hash_value + 1
    return f"/books/book_{image_index:02d}.jpg"


# 前端请求模型
class ProductListRequest(BaseModel):
    categoryID: Optional[List[int]] = None
    currentPage: int = 1
    pageSize: int = 20


class ProductSearchRequest(BaseModel):
    search: str
    currentPage: int = 1
    pageSize: int = 20


class ProductDetailsRequest(BaseModel):
    productID: int


class CategoryNameRequest(BaseModel):
    categoryName: Optional[Union[str, List[str]]] = None


# 前端响应模型
class ProductListResponse(BaseModel):
    Product: List[dict]
    total: int


class ProductDetailsResponse(BaseModel):
    Product: List[dict]


class ProductPictureResponse(BaseModel):
    ProductPicture: List[dict]


class CategoryResponse(BaseModel):
    category: List[dict]


def convert_item_to_product(item: ItemResponse) -> dict:
    """将ItemResponse转换为前端期望的Product格式
    
    前端 MyList.vue 期望的字段：
    - product_id
    - product_picture
    - product_name
    - product_title
    - product_selling_price
    - product_price
    - category_id
    """
    price = float(item.price) if item.price else 29.99
    
    # 使用本地图书封面图片
    image_url = get_book_image_path(item.item_id)
    
    return {
        # 下划线命名（前端 MyList.vue 使用）
        "product_id": item.item_id,
        "product_picture": image_url,
        "product_name": item.title or f"Book {item.item_id}",
        "product_title": item.description[:50] if item.description else (item.title or "优质图书"),
        "product_selling_price": price,
        "product_price": price,
        "category_id": 1,  # 默认分类ID
        
        # 驼峰命名（某些前端接口可能使用）
        "productID": item.item_id,
        "productName": item.title or f"Book {item.item_id}",
        "productPrice": price,
        "productImg": image_url,
        "productTitle": item.description[:50] if item.description else (item.title or "优质图书"),
        "productIntro": item.description or "",
        "categoryID": 1,
        "productSales": 0,
        "productRating": float(item.rating) if item.rating else 4.5,
    }


@router.post("/getAllProduct", response_model=ProductListResponse)
async def get_all_product(
    request: ProductListRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    获取所有商品（分页）
    兼容前端接口：POST /api/product/getAllProduct
    """
    service = ItemService(db)
    skip = (request.currentPage - 1) * request.pageSize
    limit = request.pageSize
    
    items = service.list_items(skip=skip, limit=limit)
    
    # 获取总数
    from app.models.item import Item
    total = db.query(Item).filter(Item.is_active == True).count()
    
    products = [convert_item_to_product(ItemResponse.model_validate(item)) for item in items]
    
    return ProductListResponse(Product=products, total=total)


@router.post("/getProductByCategory", response_model=ProductListResponse)
async def get_product_by_category(
    request: ProductListRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    按分类获取商品
    兼容前端接口：POST /api/product/getProductByCategory
    """
    service = ItemService(db)
    skip = (request.currentPage - 1) * request.pageSize
    limit = request.pageSize
    
    # 如果categoryID为空，返回所有商品
    if not request.categoryID or len(request.categoryID) == 0:
        items = service.list_items(skip=skip, limit=limit)
        from app.models.item import Item
        total = db.query(Item).filter(Item.is_active == True).count()
    else:
        # 这里需要根据categoryID查询，暂时使用第一个categoryID
        # 如果后端有category_id字段，需要修改
        category_id = request.categoryID[0]
        # 暂时返回所有商品，后续可以根据category_id映射到category名称
        items = service.list_items(skip=skip, limit=limit)
        from app.models.item import Item
        total = db.query(Item).filter(Item.is_active == True).count()
    
    products = [convert_item_to_product(ItemResponse.model_validate(item)) for item in items]
    
    return ProductListResponse(Product=products, total=total)


@router.post("/getProductBySearch", response_model=ProductListResponse)
async def get_product_by_search(
    request: ProductSearchRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    搜索商品
    兼容前端接口：POST /api/product/getProductBySearch
    """
    service = ItemService(db)
    skip = (request.currentPage - 1) * request.pageSize
    limit = request.pageSize
    
    items = service.list_items(skip=skip, limit=limit, search=request.search)
    
    # 获取搜索结果总数
    from app.models.item import Item
    from sqlalchemy import or_
    query = db.query(Item).filter(Item.is_active == True)
    if request.search:
        query = query.filter(
            or_(
                Item.title.ilike(f"%{request.search}%"),
                Item.description.ilike(f"%{request.search}%")
            )
        )
    total = query.count()
    
    products = [convert_item_to_product(ItemResponse.model_validate(item)) for item in items]
    
    return ProductListResponse(Product=products, total=total)


@router.post("/getDetails", response_model=ProductDetailsResponse)
async def get_details(
    request: ProductDetailsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    获取商品详情
    兼容前端接口：POST /api/product/getDetails
    """
    service = ItemService(db)
    item = service.get_item_by_id(request.productID)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    product = convert_item_to_product(ItemResponse.model_validate(item))
    return ProductDetailsResponse(Product=[product])


@router.post("/getDetailsPicture", response_model=ProductPictureResponse)
async def get_details_picture(
    request: ProductDetailsRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    获取商品图片
    兼容前端接口：POST /api/product/getDetailsPicture
    """
    service = ItemService(db)
    item = service.get_item_by_id(request.productID)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    # 使用本地图书封面图片
    image_url = get_book_image_path(item.item_id)
    
    # 返回商品图片列表
    pictures = [
        {
            "productPictureID": 1,
            "productID": item.item_id,
            "productPicture": image_url,
            "intro": item.title
        }
    ]
    
    return ProductPictureResponse(ProductPicture=pictures)


@router.post("/getPromoProduct", response_model=ProductListResponse)
async def get_promo_product(
    request: CategoryNameRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    获取推荐商品
    兼容前端接口：POST /api/product/getPromoProduct
    """
    service = ItemService(db)
    
    # 根据分类名称获取商品
    category = request.categoryName
    if isinstance(category, list):
        # 如果是列表，使用第一个分类
        category = category[0] if category else None
    
    # 如果分类不是 'book'，则忽略分类筛选，返回所有商品
    if category and category.lower() != 'book':
        category = None
    
    items = service.list_items(skip=0, limit=8, category=category)
    
    # 获取总数
    from app.models.item import Item
    query = db.query(Item).filter(Item.is_active == True)
    if category:
        query = query.filter(Item.category == category)
    total = query.count()
    
    products = [convert_item_to_product(ItemResponse.model_validate(item)) for item in items]
    
    return ProductListResponse(Product=products, total=total)


@router.post("/getHotProduct", response_model=ProductListResponse)
async def get_hot_product(
    request: CategoryNameRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    获取热门商品
    兼容前端接口：POST /api/product/getHotProduct
    """
    # 根据分类名称获取商品（热门商品可以按评分或销量排序）
    category = request.categoryName
    if isinstance(category, list):
        category = category[0] if category else None
    
    # 如果分类不是 'book'，则忽略分类筛选
    if category and category.lower() != 'book':
        category = None
    
    # 获取商品，按评分降序排列
    from app.models.item import Item
    query = db.query(Item).filter(Item.is_active == True)
    if category:
        query = query.filter(Item.category == category)
    
    # 按评分降序排列，如果没有评分则按创建时间
    items = query.order_by(Item.rating.desc().nulls_last(), Item.created_at.desc()).limit(8).all()
    
    total = query.count()
    
    products = [convert_item_to_product(ItemResponse.model_validate(item)) for item in items]
    
    return ProductListResponse(Product=products, total=total)


@router.post("/getCategory", response_model=CategoryResponse)
async def get_category(
    db: Session = Depends(get_db)
):
    """
    获取分类列表
    兼容前端接口：POST /api/product/getCategory
    """
    from app.models.item import Item
    from sqlalchemy import distinct
    
    # 获取所有不重复的分类
    categories = db.query(distinct(Item.category)).filter(
        Item.category.isnot(None),
        Item.is_active == True
    ).all()
    
    # 转换为前端期望的格式
    category_list = [
        {
            "category_id": idx + 1,
            "category_name": cat[0]
        }
        for idx, cat in enumerate(categories)
        if cat[0]
    ]
    
    return CategoryResponse(category=category_list)
