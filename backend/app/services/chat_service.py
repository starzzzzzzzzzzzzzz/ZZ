"""
聊天服务
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.chat import Chat, ChatMessage
from ..schemas.chat import ChatCreate, ChatMessageCreate
from ..utils.vector_store import VectorStore
from ..utils.semantic_search import semantic_search
from ..utils.context_builder import context_builder
from ..utils.llm import llm_client
from ..core.config import settings
from ..models.document import Document, DocumentChunk
import logging

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(settings.DATABASE_URL)
    
    async def create_chat(self, chat_create: ChatCreate) -> Dict[str, Any]:
        """创建新对话"""
        try:
            chat = Chat(title=chat_create.title)
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
            
            return {
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": []
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建对话失败: {str(e)}")
            raise
    
    async def get_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """获取对话详情"""
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return None
            
        return {
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "chat_id": msg.chat_id,
                    "role": msg.role,
                    "content": msg.content,
                    "references": msg.references,
                    "created_at": msg.created_at
                }
                for msg in chat.messages
            ]
        }
    
    async def list_chats(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """获取对话列表"""
        chats = self.db.query(Chat)\
            .order_by(Chat.updated_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
            
        return [
            {
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": []
            }
            for chat in chats
        ]
    
    async def delete_chat(self, chat_id: int) -> bool:
        """删除对话"""
        try:
            chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return False
            
            self.db.delete(chat)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除对话失败: {str(e)}")
            raise
    
    async def _get_relevant_documents(
        self,
        query: str,
        kb_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取相关文档
        
        Args:
            query: 用户问题
            kb_id: 知识库ID
            
        Returns:
            相关文档列表
        """
        try:
            # 重新初始化向量存储以确保使用正确的模型
            self.vector_store = VectorStore(settings.DATABASE_URL)
            
            # 1. 获取向量检索结果
            vector_results = await self.vector_store.search_similar(
                query=query,
                doc_id=None,
                limit=settings.SEMANTIC_SEARCH_CONFIG['vector_top_k'],
                score_threshold=settings.SEMANTIC_SEARCH_CONFIG['score_threshold']
            )
            
            if not vector_results:
                logger.warning("向量检索未找到相关文档")
                return []
                
            # 2. 获取所有文档块用于关键词检索
            doc_chunks = []
            if kb_id:
                chunks = self.db.query(DocumentChunk)\
                    .join(Document)\
                    .filter(Document.kb_id == kb_id)\
                    .all()
            else:
                chunks = self.db.query(DocumentChunk).all()
                
            for chunk in chunks:
                doc_chunks.append({
                    'content': chunk.content,
                    'metadata': {
                        'doc_id': str(chunk.document_id),
                        'chunk_index': chunk.chunk_index
                    }
                })
                
            # 3. 执行混合检索
            results = semantic_search.hybrid_search(
                query,
                vector_results,
                doc_chunks
            )
            
            # 4. 获取文档摘要
            abstract_chunks = []
            for result in results:
                doc_id = result['metadata']['doc_id']
                doc = self.db.query(Document).filter(Document.id == int(doc_id)).first()
                if doc:
                    # 获取文档的第一个分块（通常是摘要）
                    abstract_chunk = self.db.query(DocumentChunk)\
                        .filter(DocumentChunk.document_id == doc.id)\
                        .filter(DocumentChunk.chunk_index == 0)\
                        .first()
                    if abstract_chunk:
                        abstract_chunks.append({
                            'id': f"{doc.id}_chunk_0",
                            'content': abstract_chunk.content,
                            'metadata': {
                                'doc_id': str(doc.id),
                                'chunk_index': 0
                            },
                            'score': 1.0  # 摘要部分给予最高分
                        })
            
            # 5. 合并结果，确保摘要在前面
            final_results = abstract_chunks + results
            
            return final_results
            
        except Exception as e:
            logger.error(f"获取相关文档失败: {str(e)}")
            return vector_results  # 如果混合检索失败，返回原始向量检索结果
    
    async def add_message(
        self,
        chat_id: int,
        message: ChatMessageCreate
    ) -> Dict[str, Any]:
        """添加消息并获取回复"""
        try:
            logger.info(f"开始处理聊天消息，chat_id: {chat_id}")
            
            # 保存用户消息
            user_message = ChatMessage(
                chat_id=chat_id,
                role="user",
                content=message.content
            )
            self.db.add(user_message)
            self.db.flush()
            logger.info("用户消息保存成功")
            
            # 搜索相关文档
            logger.info("开始搜索相关文档")
            similar_chunks = await self._get_relevant_documents(message.content)
            
            if not similar_chunks:
                logger.warning("未找到相关文档内容")
                return {
                    "answer": "抱歉，我没有找到相关的文档内容来回答您的问题。请尝试换个方式提问，或者确认知识库中是否包含相关信息。",
                    "references": []
                }
            
            # 构建上下文
            context = self._build_context(similar_chunks)
            logger.info(f"构建的上下文长度: {len(context)}")
            
            # 构建提示词
            system_prompt = """你是一个专业的知识库助手。请基于提供的文档内容，用中文回答用户的问题。
如果文档内容不足以回答问题，请明确说明。

文档内容分为两部分：
1. 【文档摘要】部分包含文档的核心概述
2. 【详细内容】部分包含具体的细节信息

请按照以下格式组织回答：

【概要】
用1-2句话概括主要内容

【详细信息】
• 主要特点1
  - 具体说明（请标注信息来源）
  - 补充细节
• 主要特点2
  - 具体说明（请标注信息来源）
  - 补充细节
• 主要特点3
  - 具体说明（请标注信息来源）
  - 补充细节

【技术指标】
• 性能数据（请标注具体数值）
• 评测结果（请标注具体基准）
• 关键指标（请标注数据来源）

【总结】
简要总结核心优势和应用价值"""

            user_prompt = f"""请基于以下文档内容，回答问题。

{context}

用户问题：{message.content}

请用中文回答，注意：
1. 优先使用【文档摘要】中的核心信息
2. 使用【详细内容】补充具体细节
3. 提供具体的数据和指标
4. 标注信息的来源（文档ID和相关度）"""

            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]

            logger.info("开始生成回复")
            logger.debug(f"发送到LLM的消息: {messages}")
            
            # 调用LLM生成回复
            response = await llm_client.chat(
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                top_p=settings.LLM_TOP_P,
                frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
                presence_penalty=settings.LLM_PRESENCE_PENALTY
            )
            logger.info("回复生成成功")
            
            # 处理回复内容
            processed_content = self._process_response(response.content)
            logger.debug(f"处理后的回复内容: {processed_content}")
            
            # 保存助手回复
            assistant_message = ChatMessage(
                chat_id=chat_id,
                role="assistant",
                content=processed_content,
                references=self._process_references(similar_chunks)
            )
            self.db.add(assistant_message)
            self.db.commit()
            logger.info("助手回复保存成功")
            
            return {
                "answer": processed_content,
                "references": self._process_references(similar_chunks)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理聊天消息失败: {str(e)}", exc_info=True)
            raise
            
    def _process_response(self, content: str) -> str:
        """处理模型回复
        
        Args:
            content: 原始回复内容
            
        Returns:
            处理后的回复内容
        """
        # 去除<think>标签之间的内容
        import re
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        # 去除多余的空行
        content = re.sub(r'\n+', '\n', content).strip()
        return content
    
    async def add_message_stream(
        self,
        chat_id: int,
        message: ChatMessageCreate
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式添加消息并获取回复"""
        try:
            # 保存用户消息
            user_message = ChatMessage(
                chat_id=chat_id,
                role="user",
                content=message.content
            )
            self.db.add(user_message)
            self.db.flush()
            
            # 先返回用户消息
            yield {
                "type": "message",
                "message": {
                    "id": user_message.id,
                    "chat_id": user_message.chat_id,
                    "role": user_message.role,
                    "content": user_message.content,
                    "references": None,
                    "created_at": user_message.created_at
                }
            }
            
            # 搜索相关文档
            similar_chunks = await self._get_relevant_documents(message.content)
            
            # 构建上下文
            context = self._build_context(similar_chunks)
            
            # 获取历史消息
            history = self._get_chat_history(chat_id)
            
            # 生成回复（流式）
            content_buffer = []
            async for chunk in self._generate_response_stream(
                message.content,
                context,
                history
            ):
                content_buffer.append(chunk.content)
                yield {
                    "type": "token",
                    "token": chunk.content
                }
            
            # 保存完整的助手回复
            assistant_message = ChatMessage(
                chat_id=chat_id,
                role="assistant",
                content="".join(content_buffer),
                references=self._process_references(similar_chunks)
            )
            self.db.add(assistant_message)
            
            self.db.commit()
            
            # 返回完整的助手消息
            yield {
                "type": "message",
                "message": {
                    "id": assistant_message.id,
                    "chat_id": assistant_message.chat_id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "references": assistant_message.references,
                    "created_at": assistant_message.created_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理消息失败: {str(e)}")
            raise
        
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """构建对话上下文
        
        将文档片段组织成结构化的上下文,包括文档摘要和详细内容。
        
        Args:
            chunks: 相关文档片段列表,每个片段包含content和metadata
            
        Returns:
            格式化的上下文字符串
        """
        if not chunks:
            return ""
            
        # 分离摘要和内容
        abstracts = []
        contents = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "").strip()
            
            if not content:
                continue
                
            # 判断是否为摘要
            if "abstract" in metadata.get("tags", []) or len(content) < 200:
                abstracts.append({
                    "content": content,
                    "doc_id": metadata.get("doc_id"),
                    "score": chunk.get("score", 0)
                })
            else:
                contents.append({
                    "content": content,
                    "doc_id": metadata.get("doc_id"),
                    "score": chunk.get("score", 0)
                })
                
        # 构建上下文
        context_parts = []
        
        # 添加摘要部分
        if abstracts:
            context_parts.append("【文档摘要】")
            for abstract in sorted(abstracts, key=lambda x: x["score"], reverse=True):
                context_parts.append(f"• 文档 {abstract['doc_id']} (相关度: {abstract['score']:.2f})")
                context_parts.append(f"{abstract['content']}\n")
                
        # 添加详细内容
        if contents:
            context_parts.append("【详细内容】")
            for content in sorted(contents, key=lambda x: x["score"], reverse=True):
                context_parts.append(f"• 文档 {content['doc_id']} (相关度: {content['score']:.2f})")
                context_parts.append(f"{content['content']}\n")
                
        return "\n".join(context_parts)
    
    def _get_chat_history(self, chat_id: int, limit: int = 10) -> List[Dict[str, str]]:
        """获取对话历史"""
        messages = self.db.query(ChatMessage)\
            .filter(ChatMessage.chat_id == chat_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
    
    async def _generate_response(
        self,
        query: str,
        context: str,
        history: List[Dict[str, str]]
    ) -> Any:
        """生成回复"""
        prompt = f"""基于以下文档内容回答用户的问题。如果无法从文档中找到相关信息，请说明。

文档内容：
{context}

用户问题：{query}

请提供准确、有帮助的回答，并尽可能引用文档中的具体内容。"""

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的知识库助手，负责基于文档内容回答用户问题。"
            },
            *history,
            {
                "role": "user",
                "content": prompt
            }
        ]

        return await llm_client.chat(
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            top_p=settings.LLM_TOP_P,
            frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
            presence_penalty=settings.LLM_PRESENCE_PENALTY
        )
    
    async def _generate_response_stream(
        self,
        query: str,
        context: str,
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[Any, None]:
        """流式生成回复
        
        基于查询、上下文和历史记录生成结构化的流式回答。
        
        Args:
            query: 用户问题
            context: 相关文档上下文
            history: 对话历史
            
        Yields:
            LLM回复的流式内容
        """
        prompt = f"""你是一个专业的知识库助手。请按照以下格式回答问题：

【概要】
用1-2句话概括主要内容

【详细信息】
• 主要内容1
  - 具体说明（请标注信息来源）
  - 补充细节
• 主要内容2
  - 具体说明（请标注信息来源）
  - 补充细节

【补充说明】
• 重要提示
• 注意事项
• 相关建议

【总结】
简要总结核心要点

注意：
1. 所有内容必须来自文档，不要添加未提及的信息
2. 使用清晰的层级结构和要点符号
3. 保持语言简洁直接
4. 如果文档信息不足，请明确说明

基于以下文档内容回答问题：

{context}

用户问题：{query}"""

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的知识库助手，负责基于文档内容回答用户问题。"
            },
            *history,
            {
                "role": "user",
                "content": prompt
            }
        ]

        async for chunk in llm_client.chat_stream(
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            top_p=settings.LLM_TOP_P,
            frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
            presence_penalty=settings.LLM_PRESENCE_PENALTY
        ):
            yield chunk
    
    def _process_references(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理引用信息"""
        references = []
        for chunk in chunks:
            doc = self.db.query(Document)\
                .filter(Document.id == int(chunk["metadata"]["doc_id"]))\
                .first()
            if doc:
                references.append({
                    "doc_id": doc.id,
                    "title": doc.title,
                    "content": chunk["content"],
                    "score": chunk["score"]
                })
        return references 