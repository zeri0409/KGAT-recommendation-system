"""
生成用户和商品的假数据
"""
import requests
import random
from faker import Faker
import time

fake = Faker('zh_CN')  # 使用中文数据


def generate_user_data(user_id: int):
    """
    生成用户假数据
    
    Args:
        user_id: 用户ID
    
    Returns:
        用户数据字典
    """
    return {
        'user_id': user_id,
        'username': fake.user_name() + str(user_id),  # 确保唯一性
        'email': f'user{user_id}@example.com',
        'avatar_url': f'https://api.dicebear.com/7.x/avataaars/svg?seed={user_id}',
        'password_hash': f'hashed_password_{user_id}',  # 实际应该使用bcrypt等加密
    }


def fetch_book_info(item_id: int, title: str = None, use_api: bool = True):
    """
    获取图书信息（优先使用API，失败则生成假数据）
    
    Args:
        item_id: 商品ID
        title: 可选的标题（用于搜索）
        use_api: 是否尝试使用API
    
    Returns:
        图书信息字典（包含title, description, image_url, price等字段）
    """
    # 如果没有提供标题，使用默认值
    if not title:
        title = f"Book {item_id}"
    
    # 如果不需要使用API，直接生成假数据
    if not use_api:
        return {
            'title': title,
            'description': f"这是一本关于{item_id}的书籍，提供了丰富的内容和知识。",
            'image_url': f'https://via.placeholder.com/300x400?text={title[:20]}',
            'price': round(random.uniform(9.99, 49.99), 2),
            'author': fake.name(),
            'publish_year': random.randint(1990, 2023),
            'category': random.choice(['Fiction', 'Non-Fiction', 'Science', 'History', 'Biography']),
        }
    
    # 尝试从Open Library API获取信息
    try:
        # 使用ISBN或标题搜索
        search_query = title.replace(' ', '+')
        url = f"https://openlibrary.org/search.json?q={search_query}&limit=1"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('docs') and len(data['docs']) > 0:
                book = data['docs'][0]
                
                # 获取封面图片
                cover_id = book.get('cover_i')
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
                
                # 获取作者
                authors = book.get('author_name', [])
                author = authors[0] if authors else "Unknown"
                
                # 获取出版年份
                publish_year = book.get('first_publish_year', None)
                
                return {
                    'title': book.get('title', title),
                    'description': book.get('first_sentence', [None])[0] if book.get('first_sentence') else f"这是一本关于{item_id}的书籍",
                    'image_url': cover_url or f'https://via.placeholder.com/300x400?text={title[:20]}',
                    'price': round(random.uniform(9.99, 49.99), 2),
                    'author': author,
                    'publish_year': publish_year,
                    'category': book.get('subject', ['Books'])[0] if book.get('subject') else 'Books',
                }
    except Exception as e:
        print(f"获取图书信息失败 (item_id={item_id}): {e}")
    
    # 如果API调用失败，返回默认值
    return {
        'title': title,
        'description': f"这是一本关于{item_id}的书籍，提供了丰富的内容和知识。",
        'image_url': f'https://via.placeholder.com/300x400?text={title[:20]}',
        'price': round(random.uniform(9.99, 49.99), 2),
        'author': fake.name(),
        'publish_year': random.randint(1990, 2023),
        'category': random.choice(['Fiction', 'Non-Fiction', 'Science', 'History', 'Biography']),
    }



