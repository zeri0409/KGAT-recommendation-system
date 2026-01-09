"""
认证相关API
"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_active_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    Args:
        user_data: 用户注册数据
        db: 数据库会话
    
    Returns:
        创建的用户信息
    
    Raises:
        HTTPException: 如果用户名或邮箱已存在
    """
    # 检查用户名是否已存在
    logger.info(f"尝试注册新用户: {user_data.username}")
    
    # 使用更明确的查询，并记录查询结果
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    logger.info(f"查询结果: existing_user={existing_user}, username='{user_data.username}'")
    
    if existing_user:
        logger.warning(f"用户名已存在: {user_data.username}, user_id={existing_user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
    
    # 创建新用户
    try:
        # 再次检查用户名（防止并发问题）
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            avatar_url=user_data.avatar_url
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"用户注册成功: {user_data.username}, user_id: {db_user.user_id}")
        return db_user
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"注册失败: {user_data.username}, 错误: {str(e)}", exc_info=True)
        # 检查是否是唯一性约束错误
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str or "already exists" in error_str:
            if "username" in error_str or "users_username" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已存在"
                )
            elif "email" in error_str or "users_email" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
        # 其他错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    Args:
        form_data: OAuth2表单数据（username和password）
        db: 数据库会话
    
    Returns:
        JWT令牌
    
    Raises:
        HTTPException: 如果用户名或密码错误
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未激活"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前用户（通过依赖注入获取）
    
    Returns:
        当前用户信息
    """
    return current_user


