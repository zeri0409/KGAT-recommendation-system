"""
应用配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "KGAT推荐系统API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:kgat_password@localhost:5432/kgat_recommendation"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Neo4j配置（可选）
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    USE_NEO4J: bool = False  # 是否使用Neo4j存储知识图谱（默认关闭，确保从零可跑）
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30天
    
    # CORS配置（从.env读取时，如果是逗号分隔的字符串，会自动转换为列表）
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    
    @property
    def cors_origins_list(self) -> list:
        """将CORS_ORIGINS字符串转换为列表"""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 推荐系统配置
    RECOMMENDATION_CACHE_TTL: int = 3600  # 1小时
    DEFAULT_RECOMMENDATION_LIMIT: int = 20
    
    # ML模型配置（可选）
    MODEL_PATH: Optional[str] = None
    USE_GPU: bool = False
    USE_KGAT_MODEL: bool = False  # 是否使用KGAT模型（默认关闭，确保从零可跑）
    MODEL_UPDATE_INTERVAL: int = 3600  # 模型更新间隔（秒）
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()

