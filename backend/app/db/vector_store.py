"""
向量数据库连接模块
"""
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection

from ..core.config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """向量数据库管理器"""
    
    def __init__(self):
        """初始化向量数据库管理器"""
        self.client = chromadb.PersistentClient(
            path=settings.CHROMADB_PERSIST_DIR,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        logger.info(f"ChromaDB已初始化，存储目录: {settings.CHROMADB_PERSIST_DIR}")
        
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Collection:
        """获取或创建集合"""
        try:
            return self.client.get_or_create_collection(
                name=name,
                metadata=metadata or {},
                embedding_function=None  # 使用外部embedding
            )
        except Exception as e:
            logger.error(f"获取或创建集合失败: {str(e)}")
            raise
            
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """添加文档到集合"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            return True
        except Exception as e:
            logger.error(f"添加文档到集合失败: {str(e)}")
            return False
            
    def search(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 3,
        where: Optional[Dict[str, Any]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档"""
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                embeddings=embeddings
            )
            return results
        except Exception as e:
            logger.error(f"搜索文档失败: {str(e)}")
            return []
            
    def delete_collection(self, name: str) -> bool:
        """删除集合"""
        try:
            self.client.delete_collection(name=name)
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")
            return False
            
    def reset(self) -> bool:
        """重置数据库"""
        try:
            self.client.reset()
            return True
        except Exception as e:
            logger.error(f"重置数据库失败: {str(e)}")
            return False

# 创建全局向量存储管理器实例
vector_store = VectorStoreManager() 