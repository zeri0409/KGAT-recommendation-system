#!/usr/bin/env python
"""修复 user_id 序列"""
from sqlalchemy import text
from app.database import engine

def fix_sequence():
    """修复 users 表的 user_id 序列"""
    conn = engine.connect()
    trans = conn.begin()
    try:
        # 获取当前最大 user_id
        result = conn.execute(text("SELECT MAX(user_id) FROM users;"))
        max_id = result.fetchone()[0] or 0
        print(f"当前最大 user_id: {max_id}")
        
        # 获取序列当前值
        result = conn.execute(text("SELECT last_value FROM users_user_id_seq;"))
        seq_value = result.fetchone()[0]
        print(f"序列当前值: {seq_value}")
        
        # 如果序列值小于最大 user_id，需要更新序列
        if seq_value <= max_id:
            new_value = max_id + 1
            print(f"更新序列到: {new_value}")
            conn.execute(text(f"SELECT setval('users_user_id_seq', {new_value}, false);"))
            trans.commit()
            print("✅ 序列已修复")
        else:
            print("✅ 序列值正常，无需修复")
            trans.commit()
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        trans.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_sequence()

