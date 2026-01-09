#!/usr/bin/env python
"""
推荐API测试脚本
"""
import requests
import json
from typing import Optional

BASE_URL = "http://127.0.0.1:8000"


class RecommendationAPIClient:
    """推荐API客户端"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def register(self, username: str, password: str, email: Optional[str] = None) -> dict:
        """注册新用户"""
        url = f"{self.base_url}/api/auth/register"
        data = {
            "username": username,
            "password": password
        }
        if email:
            data["email"] = email
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def login(self, username: str, password: str) -> str:
        """登录并获取Token"""
        url = f"{self.base_url}/api/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        self.token = result["access_token"]
        print(f"✅ 登录成功，Token: {self.token[:20]}...")
        return self.token
    
    def get_my_recommendations(self, limit: int = 20) -> dict:
        """获取当前用户的推荐"""
        if not self.token:
            raise ValueError("请先登录")
        
        url = f"{self.base_url}/api/recommendations/me"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_user_recommendations(self, user_id: int, limit: int = 20) -> dict:
        """获取指定用户的推荐"""
        if not self.token:
            raise ValueError("请先登录")
        
        url = f"{self.base_url}/api/recommendations/{user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def record_interaction(
        self,
        item_id: int,
        interaction_type: str = "view",
        rating: Optional[float] = None
    ) -> dict:
        """记录用户交互"""
        if not self.token:
            raise ValueError("请先登录")
        
        url = f"{self.base_url}/api/recommendations/record-interaction"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "item_id": item_id,
            "interaction_type": interaction_type
        }
        if rating is not None:
            data["rating"] = rating
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()


def main():
    """主函数 - 演示API使用"""
    print("=" * 60)
    print("推荐API测试脚本")
    print("=" * 60)
    
    client = RecommendationAPIClient()
    
    # 1. 注册新用户（如果已存在会失败，可以跳过）
    print("\n1. 尝试注册新用户...")
    try:
        result = client.register("testuser", "password123", "test@example.com")
        print(f"✅ 注册成功: {result['username']}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print("⚠️  用户已存在，继续使用登录...")
        else:
            print(f"❌ 注册失败: {e}")
            return
    
    # 2. 登录
    print("\n2. 登录...")
    try:
        client.login("testuser", "password123")
    except requests.exceptions.HTTPError as e:
        print(f"❌ 登录失败: {e}")
        if e.response.status_code == 401:
            print("   提示: 用户名或密码错误")
        return
    
    # 3. 获取推荐
    print("\n3. 获取推荐...")
    try:
        recommendations = client.get_my_recommendations(limit=10)
        print(f"✅ 获取到 {recommendations['count']} 条推荐:")
        print(f"   用户ID: {recommendations['user_id']}")
        print("\n   推荐列表:")
        for item in recommendations['recommendations']:
            print(f"     排名 {item['rank']}: 商品ID {item['item_id']}, 分数 {item['score']:.4f}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ 获取推荐失败: {e}")
        if e.response.status_code == 401:
            print("   提示: Token无效或已过期")
        elif e.response.status_code == 404:
            print("   提示: 用户不存在或没有推荐数据")
        return
    
    # 4. 记录交互（如果有推荐）
    if recommendations['recommendations']:
        print("\n4. 记录交互...")
        try:
            first_item = recommendations['recommendations'][0]
            result = client.record_interaction(
                item_id=first_item['item_id'],
                interaction_type="view"
            )
            print(f"✅ 交互记录成功: {result['message']}")
            print(f"   交互ID: {result['interaction_id']}")
        except requests.exceptions.HTTPError as e:
            print(f"❌ 记录交互失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - 访问 http://127.0.0.1:8000/docs 查看完整API文档")
    print("  - 访问 http://127.0.0.1:8000/redoc 查看ReDoc文档")
    print("  - 查看 推荐API使用指南.md 了解更多详情")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

