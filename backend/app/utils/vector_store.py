"""
向量存储工具类，用于文档的向量化和检索
"""
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
import tempfile
import chromadb
from chromadb.utils import embedding_functions
import os
from chromadb import Documents, Embeddings
from pathlib import Path
import logging
import asyncio
from datetime import datetime
import uuid
import json
import numpy as np
from chromadb.config import Settings as ChromaSettings
from chromadb.api import Collection
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.api.types import EmbeddingFunction
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..models.document import Document, DocumentMetadata, DocumentChunk

from ..db.base_class import Base

logger = logging.getLogger(__name__)

class BaseEmbeddingFunction:
    """统一的嵌入函数基类"""
    
    def __init__(self, model_name: str, is_test: bool = False):
        """初始化嵌入函数
        
        Args:
            model_name: 模型名称或路径
            is_test: 是否为测试模式
        """
        self.model_name = model_name
        self.is_test = is_test
        logger.info(f"初始化向量模型: {model_name}, 测试模式: {is_test}")
        self.model = self._initialize_model()
        
    def _initialize_model(self):
        """初始化向量模型"""
        try:
            logger.info(f"开始初始化向量模型: {self.model_name}, 测试模式: {self.is_test}")
            
            if self.is_test:
                logger.info("使用测试模式，直接返回零向量模型")
                return self._create_mock_model()
            
            # 检查模型文件是否存在
            model_path = Path(self.model_name)
            if not model_path.exists():
                logger.error(f"模型路径不存在: {model_path}")
                raise FileNotFoundError(f"模型路径不存在: {model_path}")
                
            config_path = model_path / "config.json"
            if not config_path.exists():
                logger.error(f"模型配置文件不存在: {config_path}")
                raise FileNotFoundError(f"模型配置文件不存在: {config_path}")
            
            # 读取并验证配置文件
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    hidden_size = config.get('hidden_size')
                    logger.info(f"模型配置: hidden_size={hidden_size}")
                    if hidden_size != 768:
                        logger.warning(f"模型维度不是768: {hidden_size}")
            except Exception as e:
                logger.error(f"读取模型配置失败: {str(e)}")
                
            model_file = model_path / "pytorch_model.bin"
            if not model_file.exists():
                logger.error(f"模型文件不存在: {model_file}")
                raise FileNotFoundError(f"模型文件不存在: {model_file}")
                
            logger.info(f"加载本地模型: {model_path}")
            logger.info(f"模型配置文件: {config_path}")
            logger.info(f"模型文件: {model_file}")
            
            # 确保使用正确的设备
            device = settings.EMBEDDING_DEVICE
            logger.info(f"使用设备: {device}")
                
            model = SentenceTransformer(
                str(model_path),
                device=device,
                cache_folder=str(settings.safe_model_dir),
                local_files_only=True  # 启用离线模式
            )
            
            # 验证模型输出维度
            test_text = "测试文本"
            test_embedding = model.encode([test_text], convert_to_numpy=True)
            embedding_dim = test_embedding.shape[1]
            logger.info(f"模型输出维度: {embedding_dim}")
            
            if embedding_dim != 768:
                logger.error(f"模型输出维度不正确: 期望768, 实际{embedding_dim}")
                raise ValueError(f"模型输出维度不正确: {embedding_dim}")
                
            return model
            
        except Exception as e:
            logger.error(f"初始化向量模型失败: {str(e)}")
            if self.is_test:
                logger.info("测试模式下返回零向量模型")
                return self._create_mock_model()
            raise
            
    def _create_mock_model(self):
        """创建模拟模型（用于测试）"""
        return lambda input: [[0.0] * 768 for _ in input]
        
    def __call__(self, input: List[str]) -> List[List[float]]:
        """将文本转换为向量
        
        Args:
            input: 要转换的文本列表
            
        Returns:
            文本对应的向量列表
        """
        try:
            if self.is_test:
                return self.model(input)
            embeddings = self.model.encode(input, convert_to_numpy=True).tolist()
            return embeddings
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            return [[0.0] * 768 for _ in input]

class ChineseEmbeddingFunction(BaseEmbeddingFunction):
    """中文文本向量化函数"""
    
    def __init__(self, is_test: bool = False):
        model_path = str(Path(settings.PROJECT_ROOT) / "backend/models/text2vec-base-chinese")
        logger.info(f"加载向量模型: {model_path}")
        super().__init__(
            model_name=model_path,
            is_test=is_test
        )

class VectorStore:
    """向量存储类
    
    用于管理文档的向量存储和检索
    """
    def __init__(self, db_url: str, is_test: bool = False):
        """初始化向量存储
        
        Args:
            db_url: 数据库连接URL
            is_test: 是否为测试模式，默认为False
        """
        self.db_url = db_url
        self.is_test = is_test
        self._init_database()
        self._init_vector_store()
        
    def _init_database(self):
        """初始化数据库连接"""
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def _get_db(self):
        """获取数据库会话"""
        return self.Session()
        
    def _init_vector_store(self):
        """初始化向量存储"""
        try:
            # 使用配置中定义的向量存储目录，但是要回退到项目根目录
            chromadb_dir = Path(settings.BASE_DIR).parent / "data/vector_store/chromadb"
            chromadb_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"向量存储目录: {chromadb_dir}")
            
            # 确保目录存在且有写入权限
            if not chromadb_dir.exists():
                logger.error(f"向量存储目录不存在: {chromadb_dir}")
                raise FileNotFoundError(f"向量存储目录不存在: {chromadb_dir}")
                
            if not os.access(str(chromadb_dir), os.W_OK):
                logger.error(f"向量存储目录无写入权限: {chromadb_dir}")
                raise PermissionError(f"向量存储目录无写入权限: {chromadb_dir}")
            
            self.client = chromadb.PersistentClient(path=str(chromadb_dir))
            self.embedding_function = ChineseEmbeddingFunction(is_test=self.is_test)
            logger.info(f"成功初始化向量存储: {chromadb_dir}")
        except Exception as e:
            logger.error(f"初始化向量存储失败: {str(e)}")
            raise
            
    def _ensure_embedding_function(self):
        """确保向量模型已正确初始化"""
        self.embedding_function = ChineseEmbeddingFunction(is_test=self.is_test)
        
    def _get_collection_name(self, doc_id: int) -> str:
        """生成合法的集合名称
        
        Args:
            doc_id: 文档ID
            
        Returns:
            合法的集合名称
        """
        return f"doc_{doc_id}"
        
    def _get_or_create_collection(self, name: str) -> Collection:
        """获取或创建集合
        
        Args:
            name: 集合名称
            
        Returns:
            集合对象
        """
        try:
            # 确保使用正确的向量模型
            self._ensure_embedding_function()
            
            try:
                # 尝试获取已存在的集合
                collection = self.client.get_collection(
                    name=name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"获取已存在的集合: {name}")
                return collection
            except:
                # 创建新集合
                collection = self.client.create_collection(
                    name=name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"创建新集合: {name}")
                return collection
        except Exception as e:
            logger.error(f"获取或创建集合失败: {str(e)}")
            raise
            
    async def add_document(self, doc: Document) -> bool:
        """添加文档到向量存储
        
        Args:
            doc: 文档对象
            
        Returns:
            是否添加成功
        """
        session = self.Session()
        try:
            # 确保使用正确的向量模型
            self._ensure_embedding_function()
            
            # 获取或创建集合
            collection_name = self._get_collection_name(doc.id)
            collection = self._get_or_create_collection(collection_name)
            
            # 获取文档的所有分块
            chunks = doc.chunks
            if not chunks:
                logger.warning(f"文档 {doc.id} 没有分块内容")
                return False
            
            # 添加文档块到向量存储
            for chunk in chunks:
                vector_id = f"{doc.id}_chunk_{chunk.chunk_index}"
                try:
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
                    session.add(chunk)
                except Exception as e:
                    logger.error(f"添加向量失败: {str(e)}")
                    raise
            
            # 更新文档状态
            doc.is_vectorized = True
            session.add(doc)
            session.commit()
            logger.info(f"文档 {doc.id} 向量化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
            
    async def search_similar(
        self,
        query: str,
        doc_id: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """搜索相似内容
        
        Args:
            query: 查询文本
            doc_id: 文档ID，如果为None则搜索所有文档
            limit: 返回结果数量
            score_threshold: 相似度阈值
            
        Returns:
            相似内容列表
        """
        try:
            # 确保使用正确的向量模型
            self._ensure_embedding_function()
            logger.info(f"开始搜索相似内容 - 查询: {query}, 文档ID: {doc_id}, 阈值: {score_threshold}")
            
            if doc_id is None:
                # 搜索所有集合
                all_results = []
                collection_names = self.client.list_collections()
                logger.info(f"获取到 {len(collection_names)} 个集合")
                
                for collection_name in collection_names:
                    try:
                        logger.info(f"搜索集合: {collection_name}")
                        
                        collection = self.client.get_collection(
                            name=collection_name,
                            embedding_function=self.embedding_function
                        )
                        results = collection.query(
                            query_texts=[query],
                            n_results=limit,
                            include=["metadatas", "documents", "distances"]
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
                                
                                if score < score_threshold:
                                    logger.info(f"得分低于阈值 {score_threshold}，跳过")
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
                return all_results[:limit]
            else:
                # 搜索指定集合
                collection_name = self._get_collection_name(int(doc_id))
                logger.info(f"搜索指定集合: {collection_name}")
                
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["metadatas", "documents", "distances"]
                )
                
                if not results["ids"] or not results["ids"][0]:
                    logger.warning("未找到任何结果")
                    return []
                    
                similar_chunks = []
                for i, (chunk_id, metadata, distance) in enumerate(zip(
                    results["ids"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    # 使用余弦相似度
                    score = float(1 / (1 + distance))
                    logger.info(f"文档片段 {chunk_id} 的相似度得分: {score}")
                    
                    if score < score_threshold:
                        logger.info(f"得分低于阈值 {score_threshold}，跳过")
                        continue
                        
                    similar_chunks.append({
                        "id": chunk_id,
                        "content": results["documents"][0][i],
                        "metadata": metadata,
                        "score": score
                    })
                    logger.info(f"添加结果 - ID: {chunk_id}, 得分: {score}")
                    
                logger.info(f"找到 {len(similar_chunks)} 个结果")
                return similar_chunks
                
        except Exception as e:
            logger.error(f"搜索相似内容失败: {str(e)}")
            return []

    async def delete_document(self, doc_id: int) -> bool:
        """删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            # 删除向量存储中的数据
            try:
                collection_name = self._get_collection_name(doc_id)
                collection = self.client.get_collection(collection_name)
                collection.delete()
                logger.info(f"成功删除向量集合: {collection_name}")
            except Exception as e:
                logger.warning(f"删除向量集合失败: {str(e)}")
            
            # 删除数据库中的记录
            session = self.Session()
            try:
                doc = session.query(Document).filter_by(id=doc_id).first()
                if doc:
                    session.delete(doc)
                    session.commit()
                    logger.info(f"成功删除文档记录: {doc_id}")
                return True
            except Exception as e:
                logger.error(f"删除文档记录失败: {str(e)}")
                session.rollback()
                return False
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False

    def search(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """搜索文档片段
        
        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            n_results: 返回结果数量
            where: 过滤条件
            
        Returns:
            搜索结果，包含 ids、documents、metadatas 和 distances
        """
        try:
            # 确保使用正确的向量模型
            self._ensure_embedding_function()
            
            # 获取集合
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            # 执行搜索
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                include=["metadatas", "documents", "distances"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"搜索文档片段失败: {str(e)}")
            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "distances": []
            }

# 创建向量存储实例
vector_store = VectorStore(settings.DATABASE_URL, is_test=False)  # 使用真实的本地模型 