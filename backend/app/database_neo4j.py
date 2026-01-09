"""
Neo4j图数据库连接
"""
from neo4j import GraphDatabase
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Neo4jDriver:
    """Neo4j数据库驱动类"""
    
    def __init__(self):
        self.driver: Optional[GraphDatabase.driver] = None
        # 仅在显式启用 Neo4j 时尝试连接，避免“从零启动”时被 Neo4j 影响
        if settings.USE_NEO4J:
            self._connect()
        else:
            logger.info("Neo4j已禁用（USE_NEO4J=False），将仅使用PostgreSQL存储知识图谱")
    
    def _connect(self):
        """连接到Neo4j数据库"""
        try:
            uri = settings.NEO4J_URI
            user = settings.NEO4J_USER
            password = settings.NEO4J_PASSWORD
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j连接成功")
        except Exception as e:
            logger.warning(f"Neo4j连接失败: {e}，将使用PostgreSQL存储知识图谱")
            self.driver = None
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except:
            return False
    
    def create_node(self, label: str, properties: dict):
        """
        创建节点
        
        Args:
            label: 节点标签（如User, Item, Entity）
            properties: 节点属性
        """
        if not self.driver:
            return None
        
        with self.driver.session() as session:
            query = f"CREATE (n:{label} $properties) RETURN n"
            result = session.run(query, properties=properties)
            return result.single()
    
    def create_relationship(self, from_label: str, from_id_key: str, from_id_value,
                          to_label: str, to_id_key: str, to_id_value,
                          rel_type: str, properties: dict = None):
        """
        创建关系
        
        Args:
            from_label: 起始节点标签
            from_id_key: 起始节点ID键名
            from_id_value: 起始节点ID值
            to_label: 目标节点标签
            to_id_key: 目标节点ID键名
            to_id_value: 目标节点ID值
            rel_type: 关系类型
            properties: 关系属性
        """
        if not self.driver:
            return None
        
        with self.driver.session() as session:
            if properties:
                query = f"""
                MATCH (a:{from_label} {{{from_id_key}: $from_id}})
                MATCH (b:{to_label} {{{to_id_key}: $to_id}})
                CREATE (a)-[r:{rel_type} $properties]->(b)
                RETURN r
                """
                result = session.run(
                    query,
                    from_id=from_id_value,
                    to_id=to_id_value,
                    properties=properties
                )
            else:
                query = f"""
                MATCH (a:{from_label} {{{from_id_key}: $from_id}})
                MATCH (b:{to_label} {{{to_id_key}: $to_id}})
                CREATE (a)-[r:{rel_type}]->(b)
                RETURN r
                """
                result = session.run(
                    query,
                    from_id=from_id_value,
                    to_id=to_id_value
                )
            return result.single()
    
    def find_node(self, label: str, id_key: str, id_value):
        """查找节点"""
        if not self.driver:
            return None
        
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{{id_key}: $id_value}}) RETURN n"
            result = session.run(query, id_value=id_value)
            return result.single()
    
    def get_relationships(self, label: str, id_key: str, id_value, rel_type: str = None):
        """获取节点的关系"""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            if rel_type:
                query = f"""
                MATCH (n:{label} {{{id_key}: $id_value}})-[r:{rel_type}]->(m)
                RETURN type(r) as rel_type, m
                """
            else:
                query = f"""
                MATCH (n:{label} {{{id_key}: $id_value}})-[r]->(m)
                RETURN type(r) as rel_type, m
                """
            result = session.run(query, id_value=id_value)
            return [record for record in result]
    
    def execute_query(self, query: str, parameters: dict = None):
        """执行Cypher查询"""
        if not self.driver:
            return None
        
        with self.driver.session() as session:
            if parameters:
                result = session.run(query, **parameters)
            else:
                result = session.run(query)
            return [record for record in result]


# 全局Neo4j驱动实例
neo4j_driver = Neo4jDriver()


