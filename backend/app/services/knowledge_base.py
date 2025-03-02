"""
知识库服务模块
"""
import uuid
from typing import List, Optional
from ..db.vector_store import vector_store
from ..models.knowledge_base import KnowledgeBase
from ..schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseQuery

class KnowledgeBaseService:
    """
    知识库服务类
    """
    
    @staticmethod
    async def create_knowledge_base(kb_create: KnowledgeBaseCreate) -> KnowledgeBase:
        """
        创建知识库
        """
        # 生成知识库ID
        kb_id = f"kb_{uuid.uuid4().hex[:8]}"
        
        # 创建知识库集合
        collection = vector_store.create_collection(
            name=kb_id,
            metadata={
                "name": kb_create.name,
                "description": kb_create.description,
                "tags": kb_create.tags
            }
        )
        
        # 构建知识库模型
        knowledge_base = KnowledgeBase(
            id=kb_id,
            name=kb_create.name,
            description=kb_create.description,
            tags=kb_create.tags
        )
        
        return knowledge_base
    
    @staticmethod
    async def get_knowledge_base(kb_id: str) -> Optional[KnowledgeBase]:
        """
        获取知识库信息
        """
        try:
            collection = vector_store.get_collection(name=kb_id)
            metadata = collection.metadata
            
            return KnowledgeBase(
                id=kb_id,
                name=metadata["name"],
                description=metadata.get("description"),
                tags=metadata.get("tags", []),
                doc_count=collection.count()
            )
        except ValueError:
            return None
    
    @staticmethod
    async def list_knowledge_bases(query: KnowledgeBaseQuery) -> tuple[List[KnowledgeBase], int]:
        """
        获取知识库列表
        """
        collections = vector_store.list_collections()
        
        # 过滤和分页
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        
        # 构建知识库列表
        knowledge_bases = []
        for collection in collections:
            metadata = collection.metadata
            kb = KnowledgeBase(
                id=collection.name,
                name=metadata["name"],
                description=metadata.get("description"),
                tags=metadata.get("tags", []),
                doc_count=collection.count()
            )
            knowledge_bases.append(kb)
        
        total = len(knowledge_bases)
        knowledge_bases = knowledge_bases[start:end]
        
        return knowledge_bases, total
    
    @staticmethod
    async def update_knowledge_base(kb_id: str, kb_update: KnowledgeBaseUpdate) -> Optional[KnowledgeBase]:
        """
        更新知识库信息
        """
        try:
            collection = vector_store.get_collection(name=kb_id)
            metadata = collection.metadata
            
            # 更新元数据
            if kb_update.name is not None:
                metadata["name"] = kb_update.name
            if kb_update.description is not None:
                metadata["description"] = kb_update.description
            if kb_update.tags is not None:
                metadata["tags"] = kb_update.tags
            
            collection.modify(metadata=metadata)
            
            return await KnowledgeBaseService.get_knowledge_base(kb_id)
        except ValueError:
            return None
    
    @staticmethod
    async def delete_knowledge_base(kb_id: str) -> bool:
        """
        删除知识库
        """
        try:
            vector_store.delete_collection(name=kb_id)
            return True
        except ValueError:
            return False 