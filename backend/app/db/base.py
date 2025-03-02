"""数据库初始化"""
# 导入所有模型，确保它们在 Base.metadata 中注册
from app.db.base_class import Base
from app.models.document import KnowledgeBase, Document


# 导出所有模型
__all__ = [
    "Base",
    "KnowledgeBase",
    "Document"
] 