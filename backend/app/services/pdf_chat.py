"""PDF文档问答服务

提供基于本地模型的PDF文档问答功能
"""
import logging
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import os
import sys
import tempfile
from functools import lru_cache

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from sentence_transformers import SentenceTransformer

from backend.app.core.config import settings
from backend.app.utils.pdf import PDFContent, extract_text_from_pdf

logger = logging.getLogger(__name__)

QUESTION_PROMPT = """你是一个专业的文档问答助手。请基于提供的文档内容回答用户的问题。
如果无法从文档中找到答案，请明确说明。

相关文档内容：
{context}

用户问题：{question}

请按照以下格式回答：
1. 直接回答问题
2. 解释你的回答是如何得出的
3. 如果有引用，请标明具体的出处

请用中文回答。如果文档内容与问题无关，请明确指出。"""

@lru_cache()
def get_sentence_transformer():
    """获取或创建sentence transformer模型（使用缓存）"""
    try:
        logger.info(f"正在加载向量模型: {settings.SENTENCE_TRANSFORMER_MODEL}")
        model = SentenceTransformer(
            settings.SENTENCE_TRANSFORMER_MODEL,
            device=settings.EMBEDDING_DEVICE
        )
        logger.info("向量模型加载成功")
        return model
    except Exception as e:
        logger.error(f"加载主向量模型失败: {str(e)}")
        try:
            logger.info(f"尝试加载备用模型: {settings.SENTENCE_TRANSFORMER_FALLBACK}")
            model = SentenceTransformer(
                settings.SENTENCE_TRANSFORMER_FALLBACK,
                device=settings.EMBEDDING_DEVICE
            )
            logger.info("备用向量模型加载成功")
            return model
        except Exception as e:
            logger.error(f"加载备用向量模型也失败了: {str(e)}")
            raise

class EmbeddingWrapper:
    """向量模型包装器"""
    def __init__(self, model):
        self.model = model
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self.max_retries = 3
        
    def _process_text(self, text: str) -> str:
        """预处理文本
        
        1. 移除超长Unicode字符
        2. 规范化空白字符
        3. 截断过长的文本
        """
        # 替换超长Unicode字符
        text = ''.join(char if ord(char) < 0x10000 else '?' for char in text)
        # 规范化空白字符
        text = ' '.join(text.split())
        # 截断（如果需要）
        if len(text) > settings.EMBEDDING_MAX_SEQ_LENGTH:
            text = text[:settings.EMBEDDING_MAX_SEQ_LENGTH]
        return text
        
    def _batch_process(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """批量处理文本向量化"""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # 使用 SentenceTransformer 的 encode 方法
                batch_embeddings = self.model.encode(
                    batch,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_tensor=False,  # 返回numpy数组
                    normalize_embeddings=True  # 标准化向量
                ).tolist()
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"批处理向量化失败: {str(e)}")
                # 如果批处理失败，尝试逐个处理
                for text in batch:
                    try:
                        embedding = self.model.encode(
                            text,
                            convert_to_tensor=False,
                            normalize_embeddings=True
                        ).tolist()
                        all_embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"单个文本向量化失败: {str(e)}")
                        # 使用零向量作为后备
                        embedding_size = self.model.get_sentence_embedding_dimension()
                        all_embeddings.append([0.0] * embedding_size)
        return all_embeddings
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """文档向量化"""
        if not texts:
            return []
            
        # 预处理所有文本
        processed_texts = [self._process_text(text) for text in texts]
        
        # 批量处理
        try:
            return self._batch_process(processed_texts, self.batch_size)
        except Exception as e:
            logger.error(f"文档向量化失败: {str(e)}")
            # 返回零向量作为后备
            embedding_size = self.model.get_sentence_embedding_dimension()
            return [[0.0] * embedding_size] * len(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """查询向量化"""
        if not text:
            embedding_size = self.model.get_sentence_embedding_dimension()
            return [0.0] * embedding_size
            
        processed_text = self._process_text(text)
        
        for attempt in range(self.max_retries):
            try:
                return self.model.encode(
                    processed_text,
                    convert_to_tensor=False,
                    normalize_embeddings=True
                ).tolist()
            except Exception as e:
                logger.error(f"查询向量化失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败，返回零向量
                    embedding_size = self.model.get_sentence_embedding_dimension()
                    return [0.0] * embedding_size
                    
class PDFChatService:
    """PDF文档问答服务类"""
    
    def __init__(self):
        """初始化PDF问答服务"""
        try:
            # 初始化文本分割器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.PDF_CHUNK_SIZE,
                chunk_overlap=settings.PDF_CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
            )
            
            # 初始化向量模型
            model = get_sentence_transformer()
            self.embeddings = EmbeddingWrapper(model)
            
            # 确保向量存储目录存在
            self.vector_store_dir = settings.safe_vector_store_dir
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"向量存储目录: {self.vector_store_dir}")
            
            # 初始化LLM模型
            self.llm = ChatOpenAI(
                model="local-model",
                openai_api_base=settings.LLM_API_BASE,
                openai_api_key=settings.LLM_API_KEY or "not-needed",
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                model_kwargs={"top_p": settings.LLM_TOP_P}
            )
            
            # 初始化问答提示模板
            self.prompt = ChatPromptTemplate.from_template(QUESTION_PROMPT)
            
            self.vector_store = None
            
            logger.info("PDF问答服务初始化成功")
            
        except Exception as e:
            logger.error(f"初始化PDF问答服务失败: {str(e)}", exc_info=True)
            raise

    async def load_pdf(self, pdf_path: str) -> Optional[PDFContent]:
        """加载PDF文档并创建向量存储"""
        try:
            logger.info(f"开始加载PDF文件: {pdf_path}")
            
            # 直接使用原始文件，不再复制到临时文件
            pdf_content = extract_text_from_pdf(pdf_path)
            
            if not pdf_content:
                logger.error("PDF内容提取失败")
                return None
            
            logger.info("PDF文本提取完成，开始分割文本")
            
            # 分割文本
            texts = self.text_splitter.split_text(pdf_content.full_text)
            
            if not texts:
                logger.error("文本分割后为空")
                return None
                
            logger.info(f"文本分割完成，共 {len(texts)} 个文本块，开始创建向量存储")
                
            # 创建向量存储，使用较小的批次大小
            try:
                # 分批处理向量化，避免内存溢出
                batch_size = 32
                all_texts = []
                all_metadatas = []
                
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_metadatas = [{
                        "source": f"chunk_{j}",
                        "page": f"Page {j//3 + 1}",
                        "chunk": j
                    } for j in range(i, min(i + batch_size, len(texts)))]
                    
                    all_texts.extend(batch_texts)
                    all_metadatas.extend(batch_metadatas)
                    
                    logger.info(f"处理进度: {min(i + batch_size, len(texts))}/{len(texts)}")
                
                # 使用持久化目录创建向量存储
                self.vector_store = Chroma.from_texts(
                    all_texts,
                    self.embeddings,
                    metadatas=all_metadatas,
                    persist_directory=str(self.vector_store_dir / Path(pdf_path).stem)
                )
                
                logger.info(f"向量存储创建完成，共处理 {len(texts)} 个文本块")
                return pdf_content
                
            except Exception as e:
                logger.error(f"创建向量存储失败: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"加载PDF文档时出错: {str(e)}", exc_info=True)
            return None
            
    def _get_relevant_chunks(self, question: str, k: int = 3) -> List[Document]:
        """获取相关的文本块"""
        if not self.vector_store:
            raise ValueError("未加载PDF文档")
            
        try:
            return self.vector_store.similarity_search(question, k=k)
        except Exception as e:
            logger.error(f"检索相关文本块失败: {str(e)}")
            return []
            
    def _format_context(self, docs: List[Document]) -> str:
        """格式化上下文"""
        if not docs:
            return "未找到相关内容"
            
        contexts = []
        for i, doc in enumerate(docs, 1):
            context = f"[段落{i}] "
            if "page" in doc.metadata:
                context += f"(页码: {doc.metadata['page']}) "
            context += doc.page_content
            contexts.append(context)
            
        return "\n\n".join(contexts)
            
    async def ask(self, question: str) -> Dict[str, Any]:
        """向文档提问
        
        Args:
            question: 问题文本
            
        Returns:
            包含答案和相关信息的字典
        """
        if not self.vector_store:
            return {
                "answer": "请先加载PDF文档",
                "sources": [],
                "success": False
            }
            
        try:
            # 1. 检索相关文档
            docs = self._get_relevant_chunks(question)
            if not docs:
                return {
                    "answer": "抱歉，未能找到相关内容来回答您的问题",
                    "sources": [],
                    "success": True
                }
            
            # 2. 准备上下文
            context = self._format_context(docs)
            
            # 3. 构建提示词并执行问答
            try:
                prompt_value = self.prompt.format_messages(
                    context=context,
                    question=question
                )
                response = self.llm.invoke(prompt_value)
                
                # 4. 提取源文档信息
                sources = []
                for doc in docs:
                    sources.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    })
                
                return {
                    "answer": response.content,
                    "sources": sources,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"LLM调用失败: {str(e)}")
                return {
                    "answer": "抱歉，处理您的问题时出现错误",
                    "sources": sources if 'sources' in locals() else [],
                    "success": False,
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"执行问答时出错: {str(e)}")
            return {
                "answer": f"处理问题时出错: {str(e)}",
                "sources": [],
                "success": False
            }
            
    def clear_memory(self):
        """清除对话历史（已弃用）"""
        pass  # 不再使用对话记忆 