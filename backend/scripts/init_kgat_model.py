"""
初始化KGAT模型脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    try:
        from app.ml.model_loader import initialize_kgat_model
    except Exception as e:
        logger.error("无法导入 KGAT 相关模块。请先安装 KGAT 依赖：pip install -r requirements-kgat.txt")
        logger.error(f"详细错误: {e}")
        return

    model_path = settings.MODEL_PATH
    
    if not model_path:
        logger.error("未配置模型路径，请在.env文件中设置MODEL_PATH")
        return
    
    if not os.path.exists(model_path):
        logger.error(f"模型文件不存在: {model_path}")
        logger.info("请先训练模型或检查模型路径配置")
        return
    
    logger.info(f"开始初始化KGAT模型: {model_path}")
    
    predictor = initialize_kgat_model(model_path)
    
    if predictor and predictor.is_loaded():
        logger.info("✅ KGAT模型初始化成功！")
        logger.info(f"   - 用户数: {predictor.n_users}")
        logger.info(f"   - 商品数: {predictor.n_items}")
        logger.info(f"   - 实体数: {predictor.n_entities}")
        logger.info(f"   - 关系数: {predictor.n_relations}")
        if predictor.graph:
            logger.info(f"   - 图节点数: {predictor.graph.number_of_nodes()}")
            logger.info(f"   - 图边数: {predictor.graph.number_of_edges()}")
    else:
        logger.error("❌ KGAT模型初始化失败")
        logger.info("将使用轻量级推荐算法")


if __name__ == "__main__":
    main()


