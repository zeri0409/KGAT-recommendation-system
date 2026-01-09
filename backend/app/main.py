"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base
from app.api import auth, users, items, recommendations, admin, product
import logging
from app.api.cart import router as cart_router
from app.api.order import router as order_router
from app.api.resources import router as resources_router
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库表（生产环境应该使用Alembic迁移）
# Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    if settings.USE_KGAT_MODEL and settings.MODEL_PATH:
        try:
            from app.ml.model_loader import initialize_kgat_model
            from app.ml.kgat_predictor import reload_predictor
            from app.database import SessionLocal
            
            logger.info("正在初始化KGAT模型...")
            # 创建数据库会话用于模型初始化
            db = SessionLocal()
            try:
                predictor = initialize_kgat_model(db=db)
                if predictor and predictor.is_loaded():
                    reload_predictor(settings.MODEL_PATH)
                    logger.info("✅ KGAT模型初始化成功")
                else:
                    logger.warning("⚠️ KGAT模型初始化失败，将使用轻量级推荐算法")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"⚠️ KGAT模型初始化异常: {e}，将使用轻量级推荐算法", exc_info=True)
    
    yield
    
    # 关闭时（清理资源）
    pass


app = FastAPI(
    title=settings.APP_NAME,
    description="基于知识图谱的推荐系统后端API",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(items.router, prefix="/api/items", tags=["商品"])
app.include_router(product.router, prefix="/api/product", tags=["商品（兼容接口）"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["推荐"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理员"])
app.include_router(cart_router, prefix="/api/user/shoppingCart", tags=["购物车"])
app.include_router(order_router, prefix="/api/user/order", tags=["订单"])
app.include_router(resources_router, prefix="/api/resources", tags=["资源"])

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/public/readme", response_class=PlainTextResponse)
async def get_project_readme():
    """
    返回仓库根目录 README.md（用于前端 About 页面展示）。
    说明文档已收敛到单一 README，本接口避免前端依赖已删除的 docs 目录。
    """
    repo_root = Path(__file__).resolve().parents[2]
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return PlainTextResponse("README.md not found", status_code=404)
    return PlainTextResponse(readme_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

