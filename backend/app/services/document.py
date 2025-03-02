"""
文档服务模块
"""
import uuid
from typing import List, Optional, Tuple, Dict, Any
from ..db.vector_store import vector_store
from ..db.base import Document, DocumentChunk
from ..schemas.document import DocumentUpload, DocumentUpdate, DocumentQuery
from ..utils.pdf import split_text_into_chunks
from ..utils.vector_store import VectorStore
from ..core.config import settings
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..models.document import DocumentMetadata
from ..utils.llm import llm_client

logger = logging.getLogger(__name__)

class DocumentService:
    """
    文档服务类
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore()
    
    @staticmethod
    async def upload_document(doc_upload: DocumentUpload) -> Document:
        """
        上传文档
        """
        # 生成文档ID
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # 获取知识库集合
        collection = vector_store.get_collection(name=doc_upload.kb_id)
        
        # 文本分块
        chunks = split_text_into_chunks(doc_upload.content)
        chunk_count = len(chunks)
        
        # 构建元数据
        metadata = DocumentMetadata(
            source=doc_upload.metadata.source if doc_upload.metadata else None,
            author=doc_upload.metadata.author if doc_upload.metadata else None,
            tags=doc_upload.metadata.tags if doc_upload.metadata else []
        )
        
        # 添加文档到向量存储
        collection.add(
            ids=[f"{doc_id}_{i}" for i in range(chunk_count)],
            documents=chunks,
            metadatas=[{
                "doc_id": doc_id,
                "chunk_index": i,
                "title": doc_upload.title,
                **metadata.dict(exclude_none=True)
            } for i in range(chunk_count)]
        )
        
        # 构建文档模型
        document = Document(
            id=doc_id,
            kb_id=doc_upload.kb_id,
            title=doc_upload.title,
            content=doc_upload.content,
            chunk_count=chunk_count,
            metadata=metadata
        )
        
        return document
    
    @staticmethod
    async def get_document(kb_id: str, doc_id: str) -> Optional[Document]:
        """
        获取文档信息
        """
        try:
            collection = vector_store.get_collection(name=kb_id)
            
            # 查询文档的所有分块
            result = collection.get(
                where={"doc_id": doc_id},
                include=["metadatas", "documents"]
            )
            
            if not result["ids"]:
                return None
            
            # 合并文档内容
            content = "\n".join(result["documents"])
            metadata = result["metadatas"][0]
            
            return Document(
                id=doc_id,
                kb_id=kb_id,
                title=metadata["title"],
                content=content,
                chunk_count=len(result["ids"]),
                metadata=DocumentMetadata(
                    source=metadata.get("source"),
                    author=metadata.get("author"),
                    tags=metadata.get("tags", [])
                )
            )
        except ValueError:
            return None
    
    def list_documents(
        self,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[List[Document], int]:
        """
        获取文档列表
        """
        query = self.db.query(Document)
        
        if keyword:
            query = query.filter(Document.title.ilike(f"%{keyword}%"))
            
        if tags:
            query = query.filter(Document.tags.overlap(tags))
            
        total = query.count()
        docs = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return docs, total
        
    def get_document(self, doc_id: int) -> Optional[Document]:
        """
        获取单个文档
        """
        return self.db.query(Document).filter(Document.id == doc_id).first()
        
    def create_document(self, title: str, content: str, tags: List[str]) -> Document:
        """
        创建新文档
        """
        try:
            # 创建文档记录
            doc = Document(
                title=title,
                content=content,
                tags=tags
            )
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)
            
            # 向量化处理
            self.vector_store.add_document(doc)
            
            return doc
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建文档失败: {str(e)}")
            raise
            
    def update_document(self, doc_id: int, title: str, content: str, tags: List[str]) -> Optional[Document]:
        """
        更新文档
        """
        try:
            doc = self.get_document(doc_id)
            if not doc:
                return None
                
            doc.title = title
            doc.content = content 
            doc.tags = tags
            
            self.db.commit()
            self.db.refresh(doc)
            
            # 更新向量存储
            self.vector_store.update_document(doc)
            
            return doc
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新文档失败: {str(e)}")
            raise
            
    def delete_document(self, doc_id: int) -> bool:
        """
        删除文档
        """
        try:
            doc = self.get_document(doc_id)
            if not doc:
                return False
                
            self.db.delete(doc)
            self.db.commit()
            
            # 从向量存储中删除
            self.vector_store.delete_document(doc_id)
            
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除文档失败: {str(e)}")
            raise 

    async def search_similar_chunks(self, query: str, top_k: int = 5) -> List[dict]:
        """
        搜索相似的文档片段
        """
        try:
            # 获取所有文档的集合
            collections = self.vector_store.client.list_collections()
            logger.info(f"获取到 {len(collections)} 个集合")
            
            all_results = []
            for collection_name in collections:
                try:
                    logger.info(f"搜索集合: {collection_name}")
                    results = self.vector_store.search(
                        collection_name=collection_name,
                        query_texts=[query],
                        n_results=top_k * 2  # 增加每个集合的返回结果数量
                    )
                    
                    if results["ids"] and results["ids"][0]:
                        for i, (chunk_id, metadata, distance) in enumerate(zip(
                            results["ids"][0],
                            results["metadatas"][0],
                            results["distances"][0]
                        )):
                            # 使用余弦相似度
                            score = float(1 / (1 + distance))
                            logger.info(f"文档片段 {chunk_id} 的相似度得分: {score}")
                            
                            # 使用配置文件中的阈值
                            if score < settings.SEMANTIC_SEARCH_CONFIG['score_threshold']:
                                logger.info(f"得分低于阈值 {settings.SEMANTIC_SEARCH_CONFIG['score_threshold']}，跳过")
                                continue
                                
                            all_results.append({
                                "id": chunk_id,
                                "content": results["documents"][0][i],
                                "metadata": metadata,
                                "score": score
                            })
                            logger.info(f"添加结果 - ID: {chunk_id}, 得分: {score}")
                except Exception as e:
                    logger.warning(f"搜索集合 {collection_name} 失败: {str(e)}")
                    continue
            
            # 按相似度分数排序
            all_results.sort(key=lambda x: x["score"], reverse=True)
            logger.info(f"找到 {len(all_results)} 个结果")
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"搜索相似文档片段失败: {str(e)}")
            raise
            
    def generate_answer(self, query: str, context: List[dict]) -> str:
        """
        基于上下文生成回答
        """
        try:
            # 构建提示模板
            prompt = f"""基于以下文档片段回答问题。如果无法从文档中找到答案，请说明无法回答。

问题: {query}

相关文档:
"""
            
            # 添加上下文
            for i, chunk in enumerate(context, 1):
                prompt += f"\n{i}. {chunk['content']}"
                
            # 调用 LLM 生成回答
            response = self.llm.chat(prompt)
            
            return response
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            raise
            
    def chat(self, query: str) -> dict:
        """
        文档对话
        """
        try:
            # 搜索相关文档片段
            similar_chunks = self.search_similar_chunks(query)
            
            # 生成回答
            answer = self.generate_answer(query, similar_chunks)
            
            return {
                "answer": answer,
                "references": similar_chunks
            }
        except Exception as e:
            logger.error(f"文档对话失败: {str(e)}")
            raise 