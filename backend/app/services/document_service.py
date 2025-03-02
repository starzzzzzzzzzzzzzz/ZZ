"""
文档服务模块
"""
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import shutil
import os
from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import fitz

from ..models import Document, DocumentChunk, DocumentMetadata  # 直接从 models 包导入
from ..schemas.document import DocumentUpload, DocumentUpdate, DocumentQuery, PDFUploadResponse
from ..utils.pdf import extract_text_from_pdf, split_text_into_chunks
from ..utils.vector_store import VectorStore
from ..core.config import settings
from ..utils.id_generator import IDGenerator
from ..utils.llm import llm_client

logger = logging.getLogger(__name__)

class DocumentService:
    """文档服务类"""
    
    def __init__(self, db: Session):
        """初始化文档服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.vector_store = VectorStore(settings.DATABASE_URL)

    async def create_pdf_document(
        self,
        file: UploadFile,
        kb_id: int,
        title: Optional[str] = None,
        doc_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建PDF文档
        
        Args:
            file: 上传的PDF文件
            kb_id: 知识库ID
            title: 文档标题，如果为None则使用文件名
            doc_meta: 文档元数据
            
        Returns:
            包含文档信息的字典
        """
        file_path = None
        try:
            # 参数验证
            if not kb_id or kb_id <= 0:
                raise ValueError("无效的知识库ID")
                
            if not file:
                raise ValueError("文件不能为空")
                
            if not file.filename:
                raise ValueError("文件名不能为空")
                
            if title and len(title) > 255:
                raise ValueError("标题长度不能超过255个字符")
                
            if doc_meta:
                if not isinstance(doc_meta, dict):
                    raise ValueError("元数据必须是字典格式")
                if "tags" in doc_meta and not isinstance(doc_meta["tags"], dict):
                    raise ValueError("标签必须是字典格式")
            
            logger.info(f"开始处理PDF文档: {file.filename}")
            
            # 验证文件类型
            if not file.content_type in ["application/pdf"]:
                raise ValueError(f"不支持的文件类型: {file.content_type}")
            
            # 验证文件扩展名
            if not file.filename.lower().endswith('.pdf'):
                raise ValueError("文件必须是PDF格式")
            
            # 验证文件大小
            try:
                file.file.seek(0, 2)  # 移动到文件末尾
                file_size = file.file.tell()  # 获取文件大小
                file.file.seek(0)  # 重置文件指针
                
                if file_size > settings.PDF_MAX_FILE_SIZE:
                    raise ValueError(f"文件大小超过限制: {file_size} > {settings.PDF_MAX_FILE_SIZE}")
                    
                if file_size == 0:
                    raise ValueError("文件内容为空")
            except Exception as e:
                logger.error(f"文件大小检查失败: {str(e)}")
                raise ValueError("文件读取失败")
            
            # 保存PDF文件
            try:
                upload_dir = settings.safe_upload_dir  # 使用安全路径
                if not upload_dir.exists():
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    
                safe_filename = self._get_safe_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{IDGenerator.generate_short_uuid()}_{safe_filename}"
                file_path = upload_dir / filename
                logger.info(f"保存文件到: {file_path}")
                
                # 分块读取并写入文件
                chunk_size = 8192  # 8KB chunks
                with open(file_path, "wb") as f:
                    while chunk := file.file.read(chunk_size):
                        f.write(chunk)
            except Exception as e:
                logger.error(f"文件保存失败: {str(e)}")
                if file_path and file_path.exists():
                    file_path.unlink()
                raise RuntimeError("文件保存失败")
            finally:
                file.file.close()
            
            # 提取PDF文本
            try:
                logger.info("开始提取PDF文本...")
                doc_content = extract_text_from_pdf(file_path)
                if not doc_content.success:
                    raise RuntimeError(f"PDF文本提取失败: {doc_content.error}")
                logger.info(f"提取的文本长度: {len(doc_content.full_text)} 字符")
                
                # 获取PDF页数
                page_count = doc_content.metadata.page_count
                logger.info(f"PDF页数: {page_count}")
            except Exception as e:
                logger.error(f"PDF文本提取失败: {str(e)}")
                if file_path and file_path.exists():
                    file_path.unlink()
                raise RuntimeError(f"PDF文本提取失败: {str(e)}")

            # 创建文档记录
            try:
                logger.info("创建文档记录...")
                doc = Document(
                    kb_id=kb_id,
                    title=title or file.filename,
                    content=doc_content.full_text,
                    file_path=str(file_path),
                    file_size=file_size,
                    mime_type=file.content_type,
                    page_count=page_count,
                    is_vectorized=False,
                    chunk_count=0
                )
                self.db.add(doc)
                self.db.flush()
                logger.info(f"文档ID: {doc.id}")

                # 如果有元数据，创建元数据记录
                if doc_meta:
                    logger.info("创建元数据记录...")
                    metadata = DocumentMetadata(
                        document_id=doc.id,
                        source=doc_meta.get("source"),
                        author=doc_meta.get("author"),
                        tags=doc_meta.get("tags", {})
                    )
                    self.db.add(metadata)
                    self.db.flush()

                # 创建文档分块
                logger.info("开始文本分块...")
                chunks = split_text_into_chunks(doc_content.full_text)
                if not chunks:
                    raise RuntimeError("文档分块失败")
                    
                logger.info(f"生成分块数量: {len(chunks)}")
                
                for idx, chunk_text in enumerate(chunks):
                    if not chunk_text.strip():
                        continue
                        
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        content=chunk_text,
                        chunk_index=idx,
                        page_number=None,
                        chunk_metadata={},
                        vector_id=None
                    )
                    self.db.add(chunk)
                doc.chunk_count = len(chunks)
                self.db.flush()

                # 向量化处理
                logger.info("开始向量化处理...")
                try:
                    # 获取或创建集合
                    collection_name = f"doc_{doc.id}"
                    collection = self.vector_store._get_or_create_collection(collection_name)
                    
                    # 添加文档块到向量存储
                    for chunk in doc.chunks:
                        vector_id = f"{doc.id}_chunk_{chunk.chunk_index}"
                        # 构建 metadata，确保没有 None 值
                        metadata = {
                            "doc_id": str(doc.id),
                            "chunk_index": chunk.chunk_index
                        }
                        if chunk.page_number is not None:
                            metadata["page_number"] = chunk.page_number

                        collection.add(
                            documents=[chunk.content],
                            ids=[vector_id],
                            metadatas=[metadata]
                        )
                        logger.info(f"成功添加向量: {vector_id}")
                        # 更新chunk的vector_id
                        chunk.vector_id = vector_id
                        self.db.add(chunk)
                    
                    # 更新文档状态
                    doc.is_vectorized = True
                    self.db.add(doc)
                    logger.info("向量化处理成功")
                except Exception as e:
                    logger.error(f"向量化处理失败: {str(e)}")
                    raise RuntimeError(f"向量化处理失败: {str(e)}")

                # 提交事务
                self.db.commit()
                logger.info("文档记录保存成功")

                # 返回成功响应
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "id": doc.id,
                        "title": doc.title,
                        "file_size": doc.file_size,
                        "page_count": doc.page_count,
                        "chunk_count": doc.chunk_count,
                        "created_at": doc.created_at.isoformat(),
                        "is_vectorized": doc.is_vectorized
                    }
                }
            except Exception as e:
                logger.error(f"创建文档记录失败: {str(e)}")
                if file_path and file_path.exists():
                    file_path.unlink()
                self.db.rollback()
                raise RuntimeError(f"创建文档记录失败: {str(e)}")
                
        except ValueError as e:
            self.db.rollback()
            if file_path and file_path.exists():
                file_path.unlink()
            logger.error(f"参数验证失败: {str(e)}")
            return {
                "code": 400,
                "message": str(e),
                "data": None
            }
        except RuntimeError as e:
            self.db.rollback()
            if file_path and file_path.exists():
                file_path.unlink()
            logger.error(f"创建PDF文档失败: {str(e)}")
            return {
                "code": 500,
                "message": str(e),
                "data": None
            }
        except Exception as e:
            self.db.rollback()
            if file_path and file_path.exists():
                file_path.unlink()
            logger.error(f"创建PDF文档失败: {str(e)}")
            return {
                "code": 500,
                "message": "创建PDF文档失败，请稍后重试",
                "data": None
            }

    def _get_safe_filename(self, filename: str) -> str:
        """获取安全的文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        # 移除路径分隔符和空白字符
        filename = os.path.basename(filename)
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        # 限制长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        return filename

    def list_documents(
        self,
        kb_id: int,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取文档列表"""
        try:
            logger.info(f"开始获取文档列表: kb_id={kb_id}, page={page}, page_size={page_size}, keyword={keyword}")
            
            # 基础查询
            query = self.db.query(Document)
            logger.info("创建基础查询")
            
            # 添加知识库ID过滤
            query = query.filter(Document.kb_id == kb_id)
            logger.info(f"添加知识库过滤: kb_id={kb_id}")
            
            # 关键词过滤
            if keyword:
                query = query.filter(Document.title.ilike(f"%{keyword}%"))
                logger.info(f"添加关键词过滤: keyword={keyword}")
            
            # 获取总数
            total = query.count()
            logger.info(f"查询到文档总数: {total}")
            
            # 如果没有记录，直接返回空列表
            if total == 0:
                logger.info("没有找到任何文档")
                return [], 0
            
            # 分页查询
            documents = query.order_by(Document.created_at.desc())\
                .offset((page - 1) * page_size)\
                .limit(page_size)\
                .all()
            
            logger.info(f"当前页文档数量: {len(documents)}")
            
            # 转换为字典列表
            result = []
            for doc in documents:
                try:
                    logger.info(f"处理文档: id={doc.id}, title={doc.title}, type={type(doc)}")
                    logger.info(f"文档属性: {dir(doc)}")
                    logger.info(f"文档字典: {doc.__dict__}")
                    
                    doc_dict = {
                        "id": doc.id,
                        "kb_id": doc.kb_id,
                        "title": doc.title,
                        "content": None,  # 列表中不返回内容
                        "file_path": doc.file_path,
                        "file_size": doc.file_size,
                        "mime_type": doc.mime_type,
                        "page_count": doc.page_count,
                        "vector_store_path": doc.vector_store_path,
                        "chunk_count": doc.chunk_count,
                        "is_vectorized": doc.is_vectorized,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
                    }
                    result.append(doc_dict)
                    logger.info(f"成功处理文档: {doc_dict}")
                except Exception as e:
                    logger.error(f"处理文档失败: error={str(e)}", exc_info=True)
                    continue
            
            logger.info(f"成功返回 {len(result)} 个文档")
            logger.info(f"返回数据: {result}")
            return result, total
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
            return [], 0

    def delete_document(self, doc_id: int) -> bool:
        """删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 查找文档
            doc = self.db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                return False
            
            # 删除文件
            if doc.file_path and Path(doc.file_path).exists():
                Path(doc.file_path).unlink()
            
            # 删除向量存储
            if doc.is_vectorized:
                collection_name = f"doc_{doc.id}"
                try:
                    self.vector_store.delete_collection(collection_name)
                except Exception as e:
                    logger.error(f"删除向量存储失败: {str(e)}")
            
            # 删除数据库记录
            self.db.delete(doc)
            self.db.commit()
            
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            self.db.rollback()
            return False

    async def vectorize_all_documents(self) -> bool:
        """重新向量化所有文档
        
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 获取所有文档
            documents = self.db.query(Document).all()
            if not documents:
                logger.warning("没有找到需要向量化的文档")
                return True
                
            logger.info(f"开始向量化 {len(documents)} 个文档")
            
            # 2. 清空现有的向量存储
            try:
                collections = self.vector_store.client.list_collections()
                for collection_name in collections:
                    logger.info(f"删除集合: {collection_name}")
                    self.vector_store.client.delete_collection(collection_name)
            except Exception as e:
                logger.error(f"清空向量存储失败: {str(e)}")
                raise
            
            # 3. 重新向量化每个文档
            for doc in documents:
                try:
                    logger.info(f"开始向量化文档: {doc.id} - {doc.title}")
                    
                    # 获取或创建集合
                    collection_name = self.vector_store._get_collection_name(doc.id)
                    collection = self.vector_store._get_or_create_collection(collection_name)
                    
                    # 添加文档块到向量存储
                    for chunk in doc.chunks:
                        vector_id = f"{doc.id}_chunk_{chunk.chunk_index}"
                        try:
                            # 构建 metadata
                            metadata = {
                                "doc_id": str(doc.id),
                                "chunk_index": chunk.chunk_index
                            }
                            if chunk.page_number is not None:
                                metadata["page_number"] = chunk.page_number

                            collection.add(
                                documents=[chunk.content],
                                ids=[vector_id],
                                metadatas=[metadata]
                            )
                            logger.info(f"成功添加向量: {vector_id}")
                            
                            # 更新chunk的vector_id
                            chunk.vector_id = vector_id
                            self.db.add(chunk)
                        except Exception as e:
                            logger.error(f"添加向量失败: {str(e)}")
                            raise
                    
                    # 更新文档状态
                    doc.is_vectorized = True
                    self.db.add(doc)
                    self.db.flush()
                    logger.info(f"文档 {doc.id} 向量化完成")
                    
                except Exception as e:
                    logger.error(f"向量化文档 {doc.id} 失败: {str(e)}")
                    self.db.rollback()
                    raise
            
            # 4. 提交所有更改
            self.db.commit()
            logger.info("所有文档向量化完成")
            return True
            
        except Exception as e:
            logger.error(f"向量化文档失败: {str(e)}")
            self.db.rollback()
            return False

    async def search_similar_chunks(self, query: str, top_k: int = 3) -> List[dict]:
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
                        n_results=top_k
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
