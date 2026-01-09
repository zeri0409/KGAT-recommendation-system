#!/usr/bin/env python
"""直接测试注册函数"""
import sys
from app.database import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.api.auth import register
import time

# 创建测试数据
username = f"testdirect_{int(time.time() * 1000)}"
user_data = UserCreate(
    username=username,
    password="test123456"
)

print(f"尝试注册用户名: {username}")

# 直接检查数据库
db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == username).first()
    print(f"数据库中是否存在: {'是' if existing else '否'}")
    
    if not existing:
        # 尝试创建用户
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash="test_hash",
            avatar_url=user_data.avatar_url
        )
        db.add(db_user)
        db.commit()
        print(f"✅ 用户创建成功: {db_user.user_id}")
        
        # 删除测试用户
        db.delete(db_user)
        db.commit()
        print("✅ 测试用户已删除")
    else:
        print("❌ 用户已存在")
finally:
    db.close()

