"""初始化数据库"""
import logging
from sqlalchemy import create_engine
from app.core.config import settings
from app.db.base_class import Base
from app.models.document import KnowledgeBase, Document, DocumentMetadata, DocumentChunk

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """初始化数据库"""
    try:
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        logger.info(f"连接数据库: {settings.DATABASE_URL}")
        
        # 删除所有表（如果存在）
        Base.metadata.drop_all(bind=engine)
        logger.info("删除所有已存在的表")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("创建所有表")
        
        logger.info("数据库初始化完成！")
        
    except Exception as e:
        logger.error(f"初始化数据库失败: {str(e)}")
        raise

if __name__ == "__main__":
    init_db() 