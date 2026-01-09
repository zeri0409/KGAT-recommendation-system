"""
Pydantic模型（API请求/响应）
"""
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.schemas.interaction import InteractionCreate, InteractionResponse
from app.schemas.recommendation import RecommendationResponse
from app.schemas.auth import Token, TokenData

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "InteractionCreate",
    "InteractionResponse",
    "RecommendationResponse",
    "Token",
    "TokenData",
]


