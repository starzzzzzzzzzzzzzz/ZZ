"""
知识库服务模块
"""
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, select, exists
import logging
from datetime import datetime

from ..models.document import KnowledgeBase, Document
from ..schemas.document import KnowledgeBaseCreate, KnowledgeBaseUpdate

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """知识库服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_knowledge_base(self, kb_create: KnowledgeBaseCreate) -> Dict[str, Any]:
        """创建知识库"""
        try:
            kb = KnowledgeBase(
                name=kb_create.name,
                description=kb_create.description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(kb)
            self.db.commit()
            self.db.refresh(kb)
            
            # 返回字典而不是模型实例
            return {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
                "document_count": 0
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建知识库失败: {str(e)}")
            raise
    
    def get_knowledge_base(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库"""
        try:
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return None
                
            # 获取文档数量
            doc_count = self.db.query(Document).filter(Document.kb_id == kb_id).count()
                
            return {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
                "document_count": doc_count
            }
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None
    
    def list_knowledge_bases(
        self,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取知识库列表"""
        try:
            # 首先检查知识库表是否存在
            table_exists = self.db.execute(
                select(exists().select_from(KnowledgeBase))
            ).scalar()
            
            if not table_exists:
                logger.warning("知识库表不存在")
                return [], 0
            
            # 基础查询
            query = self.db.query(KnowledgeBase)
            
            # 关键词过滤
            if keyword:
                query = query.filter(KnowledgeBase.name.ilike(f"%{keyword}%"))
            
            # 获取总数
            total = query.count()
            
            # 如果没有记录，直接返回空列表
            if total == 0:
                return [], 0
            
            # 分页查询知识库
            knowledge_bases = query.order_by(KnowledgeBase.created_at.desc())\
                .offset((page - 1) * page_size)\
                .limit(page_size)\
                .all()
            
            # 转换为字典列表
            result = []
            for kb in knowledge_bases:
                # 获取文档数量 - 只查询count
                doc_count = self.db.query(func.count(Document.id))\
                    .filter(Document.kb_id == kb.id)\
                    .scalar() or 0
                
                kb_dict = {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "created_at": kb.created_at.isoformat() if kb.created_at else None,
                    "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
                    "document_count": doc_count
                }
                result.append(kb_dict)
            
            return result, total
            
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return [], 0
    
    def update_knowledge_base(
        self,
        kb_id: int,
        kb_update: KnowledgeBaseUpdate
    ) -> Optional[Dict[str, Any]]:
        """更新知识库"""
        try:
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return None
                
            if kb_update.name is not None:
                kb.name = kb_update.name
            if kb_update.description is not None:
                kb.description = kb_update.description
                
            kb.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(kb)
            
            # 获取文档数量
            doc_count = self.db.query(Document).filter(Document.kb_id == kb_id).count()
                
            return {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
                "document_count": doc_count
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新知识库失败: {str(e)}")
            raise
    
    def delete_knowledge_base(self, kb_id: int) -> bool:
        """删除知识库"""
        try:
            # 先检查知识库是否存在
            kb = self.db.query(KnowledgeBase)\
                .filter(KnowledgeBase.id == kb_id)\
                .first()
            if not kb:
                logger.warning(f"知识库不存在: {kb_id}")
                return False

            # 删除知识库（级联删除会自动删除相关文档）
            self.db.delete(kb)
            self.db.commit()
            logger.info(f"成功删除知识库: {kb_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除知识库失败: {str(e)}", exc_info=True)
            raise 