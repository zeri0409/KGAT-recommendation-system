"""
资源接口适配层 - 兼容前端旧接口
处理轮播图、静态资源等请求
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from pydantic import BaseModel

router = APIRouter()


class CarouselItem(BaseModel):
    carousel_id: int
    imgPath: str
    describes: Optional[str] = None


class CarouselResponse(BaseModel):
    carousel: List[CarouselItem]


@router.post("/carousel")
async def get_carousel(db: Session = Depends(get_db)):
    """
    获取轮播图数据
    兼容前端接口：POST /api/resources/carousel
    """
    # 返回模拟的轮播图数据
    # 可以后续从数据库获取或配置文件读取
    carousel_data = [
        {
            "carousel_id": 1,
            "imgPath": "public/imgs/carousel/carousel1.jpg",
            "describes": "推荐商品1"
        },
        {
            "carousel_id": 2,
            "imgPath": "public/imgs/carousel/carousel2.jpg",
            "describes": "推荐商品2"
        },
        {
            "carousel_id": 3,
            "imgPath": "public/imgs/carousel/carousel3.jpg",
            "describes": "推荐商品3"
        },
        {
            "carousel_id": 4,
            "imgPath": "public/imgs/carousel/carousel4.jpg",
            "describes": "推荐商品4"
        }
    ]
    
    return {"carousel": carousel_data}


@router.get("/carousel")
async def get_carousel_get(db: Session = Depends(get_db)):
    """
    获取轮播图数据（GET方式）
    """
    return await get_carousel(db)
