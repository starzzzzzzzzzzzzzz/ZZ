"""
PDF文档处理和向量存储集成测试

本测试模块验证PDF文档的处理流程，包括：
1. PDF文本提取
2. 文本清理和规范化
3. 文档分块
4. 向量存储集成
5. 文档检索功能
"""
import pytest
import pytest_asyncio
from pathlib import Path
import logging
import sys
import os
from typing import AsyncGenerator, Any
from backend.app.core.config import Settings
from backend.app.utils.vector_store import VectorStore
from backend.app.models.document import Document, DocumentMetadata
from backend.app.utils.pdf import extract_text_from_pdf

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# pytest-asyncio配置
pytest_plugins = ('pytest_asyncio',)
pytestmark = pytest.mark.asyncio

# 设置默认的事件循环作用域
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "module"

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
    
    try:
        store.client.get_collection("test_kb")
    except:
        store.client.create_collection(
            name="test_kb",
            embedding_function=store.embedding_function
        )
    
    yield store

async def cleanup_test_document(vector_store: VectorStore, doc_id: str):
    """清理测试文档
    
    Args:
        vector_store: 向量存储实例
        doc_id: 要清理的文档ID
    """
    logger.info(f"清理文档: {doc_id}")
    session = vector_store.Session()
    try:
        old_doc = session.query(vector_store.DocumentModel).filter_by(id=doc_id).first()
        if old_doc:
            logger.info("发现旧文档，正在删除...")
            session.delete(old_doc)
            session.commit()
            logger.info("旧文档已删除")
    except Exception as e:
        logger.warning(f"清理文档时出错: {str(e)}")
        session.rollback()
    finally:
        session.close()

@pytest.mark.asyncio
async def test_pdf_processing(vector_store: VectorStore):
    """测试PDF文档处理完整流程
    
    测试步骤：
    1. 清理可能存在的旧测试文档
    2. 验证PDF文件存在性
    3. 提取PDF文本内容
    4. 创建文档对象并添加到向量存储
    5. 验证文档存储和分块
    6. 测试文档检索功能
    """
    # 获取PDF文件路径
    workspace_root = Path(os.getcwd()).parent  # 返回到项目根目录
    pdf_path = workspace_root / "docs" / "2501.12948v1.pdf"
    
    logger.info(f"当前工作目录: {workspace_root}")
    logger.info(f"PDF文件路径: {pdf_path}")
    
    assert pdf_path.exists(), f"PDF文件不存在：{pdf_path}"
    
    try:
        # 清理旧文档
        await cleanup_test_document(vector_store, "pdf_test_doc")

        # 提取文本
        logger.info("开始提取PDF文本...")
        text = extract_text_from_pdf(str(pdf_path))
        assert text is not None and len(text) > 0, "PDF文本提取失败"
        logger.info(f"成功提取文本，长度：{len(text)}")
        
        # 打印文本预览
        logger.info("文本预览(前500字符):")
        logger.info(text[:500])
        
        # 创建文档对象
        doc = Document(
            id="pdf_test_doc",
            kb_id="test_kb",
            title="DeepSeek-R1 Paper",
            content=text,
            metadata=DocumentMetadata(
                source=pdf_path.name,
                author="DeepSeek-AI",
                tags=["AI", "LLM", "Research"]
            )
        )
        
        # 添加文档到向量存储
        logger.info("开始添加文档到向量存储...")
        await vector_store.add_document(doc)
        logger.info("文档添加成功")
        
        # 验证文档存储
        logger.info("验证文档存储...")
        session = vector_store.Session()
        try:
            db_doc = session.query(vector_store.DocumentModel).filter_by(id=doc.id).first()
            assert db_doc is not None, "文档未成功存储"
            assert len(db_doc.chunks) > 0, "文档未被正确分块"
            logger.info(f"文档分块数量：{len(db_doc.chunks)}")
            
            # 验证分块内容
            if len(db_doc.chunks) > 0:
                logger.info("第一个分块内容预览:")
                logger.info(db_doc.chunks[0].content[:200])
            
            # 测试文档检索
            logger.info("测试文档检索功能...")
            search_queries = [
                "machine learning",
                "reinforcement learning",
                "model architecture"
            ]
            
            for query in search_queries:
                logger.info(f"执行搜索查询: {query}")
                results = await vector_store.search_documents(
                    query,
                    "test_kb",
                    limit=3
                )
                logger.info(f"搜索到 {len(results)} 个结果")
                
                assert len(results) > 0, f"查询'{query}'未返回结果"
                
                # 打印搜索结果
                for i, result in enumerate(results, 1):
                    logger.info(f"结果 {i}:")
                    logger.info(f"标题: {result.title}")
                    logger.info(f"内容片段: {result.content[:200]}...")
                    logger.info("-" * 50)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        raise 