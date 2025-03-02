"""
测试向量存储和ID生成功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
import logging
from pathlib import Path
from typing import AsyncGenerator

from backend.app.utils.vector_store import VectorStore
from backend.app.utils.id_generator import IDGenerator
from backend.app.models.document import Document, DocumentMetadata
from backend.app.core.config import Settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_knowledge_base"

@pytest.fixture(scope="module")
def test_settings() -> Settings:
    """创建测试配置实例"""
    class TestSettings(Settings):
        DATABASE_URL: str = DATABASE_URL
        is_test: bool = True
    
    return TestSettings()

@pytest_asyncio.fixture(scope="module")
async def vector_store(test_settings: Settings) -> AsyncGenerator[VectorStore, None]:
    """创建向量存储实例"""
    store = VectorStore(
        db_url=test_settings.DATABASE_URL,
        is_test=True
    )
    yield store

@pytest.mark.asyncio
async def test_id_generation_and_uniqueness(vector_store: VectorStore):
    """测试ID生成和唯一性"""
    # 1. 测试文档ID生成
    kb_id = "test_kb"
    title = "测试文档"
    doc_id1 = vector_store.id_generator.generate_doc_id(kb_id, title)
    doc_id2 = vector_store.id_generator.generate_doc_id(kb_id, title)
    
    # 验证两个文档ID不同（因为包含时间戳）
    assert doc_id1 != doc_id2
    assert doc_id1.startswith("doc_")
    assert doc_id2.startswith("doc_")
    
    # 2. 测试分块ID生成
    chunk_id1 = vector_store.id_generator.generate_chunk_id(doc_id1, 0)
    chunk_id2 = vector_store.id_generator.generate_chunk_id(doc_id1, 1)
    
    # 验证分块ID格式和唯一性
    assert chunk_id1 != chunk_id2
    assert chunk_id1.startswith("chunk_")
    assert chunk_id2.startswith("chunk_")
    
    # 3. 测试向量ID生成
    vector_id1 = vector_store.id_generator.generate_vector_id(doc_id1, chunk_id1)
    vector_id2 = vector_store.id_generator.generate_vector_id(doc_id1, chunk_id2)
    
    # 验证向量ID格式和唯一性
    assert vector_id1 != vector_id2
    assert vector_id1.startswith("vec_")
    assert vector_id2.startswith("vec_")

@pytest.mark.asyncio
async def test_document_processing(vector_store: VectorStore):
    """测试文档处理流程"""
    # 1. 准备测试文档
    doc = Document(
        kb_id="test_kb",
        title="测试文档",
        content="这是一个测试文档的内容。\n\n包含多个段落。\n\n用于测试文档处理功能。",
        metadata=DocumentMetadata(
            source="test",
            author="tester",
            tags=["test", "demo"]
        )
    )
    
    # 2. 添加文档
    try:
        await vector_store.add_document(doc)
        logger.info(f"文档添加成功: {doc.id}")
        
        # 3. 验证文档是否正确存储
        session = vector_store.Session()
        try:
            db_doc = session.query(vector_store.DocumentModel).filter_by(id=doc.id).first()
            assert db_doc is not None
            assert db_doc.title == doc.title
            assert len(db_doc.chunks) > 0
            
            # 验证分块
            for chunk in db_doc.chunks:
                assert chunk.vector_id.startswith("vec_")
                assert chunk.content is not None
                
            logger.info(f"文档验证成功，包含 {len(db_doc.chunks)} 个分块")
            
        finally:
            session.close()
            
        # 4. 测试文档搜索
        results = await vector_store.search_documents(
            query="测试文档",
            kb_id="test_kb",
            limit=5
        )
        
        assert len(results) > 0
        assert results[0].id == doc.id
        assert results[0].title == doc.title
        logger.info("搜索测试成功")
        
        # 5. 测试文档删除
        success = await vector_store.delete_document(doc.id, "test_kb")
        assert success
        logger.info("文档删除成功")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_id_conflict_handling(vector_store: VectorStore):
    """测试ID冲突处理"""
    # 1. 准备两个相同内容的文档
    content = "测试文档内容"
    doc1 = Document(
        kb_id="test_kb",
        title="测试文档",
        content=content,
        metadata=DocumentMetadata(
            source="test",
            author="tester",
            tags=["test"]
        )
    )
    
    doc2 = Document(
        kb_id="test_kb",
        title="测试文档",
        content=content,
        metadata=DocumentMetadata(
            source="test",
            author="tester",
            tags=["test"]
        )
    )
    
    try:
        # 2. 添加第一个文档
        await vector_store.add_document(doc1)
        logger.info(f"第一个文档添加成功: {doc1.id}")
        
        # 3. 添加第二个文档
        await vector_store.add_document(doc2)
        logger.info(f"第二个文档添加成功: {doc2.id}")
        
        # 4. 验证两个文档的ID不同
        assert doc1.id != doc2.id
        
        # 5. 清理测试数据
        await vector_store.delete_document(doc1.id, "test_kb")
        await vector_store.delete_document(doc2.id, "test_kb")
        logger.info("测试数据清理完成")
        
    except Exception as e:
        logger.error(f"测试ID冲突处理时出错: {str(e)}")
        raise 