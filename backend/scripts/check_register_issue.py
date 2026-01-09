#!/usr/bin/env python
"""检查注册问题"""
import sys
import logging
from app.database import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_register_logic(username: str):
    """测试注册逻辑"""
    print(f"\n{'='*60}")
    print(f"测试用户名: {username}")
    print(f"{'='*60}")
    
    # 创建数据库会话
    db = SessionLocal()
    try:
        # 步骤1: 检查用户名是否存在
        print("\n步骤1: 检查用户名是否存在")
        existing_user = db.query(User).filter(User.username == username).first()
        print(f"  查询结果: {existing_user}")
        if existing_user:
            print(f"  ❌ 用户名已存在: user_id={existing_user.user_id}")
            return False
        else:
            print(f"  ✅ 用户名不存在，可以注册")
        
        # 步骤2: 尝试创建用户
        print("\n步骤2: 尝试创建用户")
        try:
            db_user = User(
                username=username,
                email=None,
                password_hash=get_password_hash("test123456"),
                avatar_url=None
            )
            db.add(db_user)
            db.flush()  # 刷新但不提交，检查是否有错误
            print(f"  ✅ 用户对象创建成功")
            
            # 检查是否有唯一性约束错误
            db.commit()
            print(f"  ✅ 用户提交成功: user_id={db_user.user_id}")
            
            # 清理：删除测试用户
            db.delete(db_user)
            db.commit()
            print(f"  ✅ 测试用户已删除")
            return True
            
        except Exception as e:
            db.rollback()
            print(f"  ❌ 创建用户失败: {e}")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    import time
    # 测试1: 使用时间戳
    username1 = f"test_{int(time.time() * 1000000)}"
    test_register_logic(username1)
    
    # 测试2: 使用固定用户名（应该不存在）
    username2 = "test_unique_xyz123abc"
    test_register_logic(username2)

