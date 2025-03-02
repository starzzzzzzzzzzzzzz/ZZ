"""
对话服务层，处理对话相关的业务逻辑
"""
import time
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

from ..models.chat import ChatHistory
from ..db.base import Document
from ..schemas.chat import ChatQuery, ChatResponse, Reference, ChatMetadata, ChatHistoryQuery
from ..core.config import settings
from ..core.errors import NotFoundError
from ..utils.vector_store import VectorStore

class ChatService:
    """对话服务类"""
    
    @staticmethod
    async def chat(chat_query: ChatQuery) -> ChatResponse:
        """
        处理对话请求
        
        Args:
            chat_query: 对话请求参数
            
        Returns:
            对话响应
            
        Raises:
            NotFoundError: 知识库不存在
        """
        start_time = time.time()
        
        # 1. 向量检索相关文档
        search_params = chat_query.search_params or {}
        results = await VectorStore.search(
            collection_name=chat_query.kb_id,
            query=chat_query.query,
            top_k=search_params.get("top_k", 3),
            score_threshold=search_params.get("score_threshold", 0.6)
        )
        
        if not results:
            raise NotFoundError(f"Knowledge base {chat_query.kb_id} not found")
            
        # 2. 构建上下文
        context = "\n".join([doc.content for doc in results])
        
        # 3. 调用LLM生成回答
        messages = []
        if chat_query.history:
            messages.extend([{"role": msg.role, "content": msg.content} for msg in chat_query.history])
        messages.append({"role": "user", "content": f"基于以下内容回答问题:\n\n{context}\n\n问题: {chat_query.query}"})
        
        response = await settings.LLM_CLIENT.chat(messages=messages)
        
        # 4. 构建引用来源
        references = []
        for doc in results:
            references.append(Reference(
                doc_id=doc.id,
                doc_title=doc.metadata.get("title", ""),
                content=doc.content,
                score=doc.score
            ))
            
        # 5. 记录对话历史
        chat_history = ChatHistory(
            kb_id=chat_query.kb_id,
            query=chat_query.query,
            answer=response.content,
            references=[ref.dict() for ref in references],
            metadata={
                "tokens": response.usage.total_tokens,
                "latency": (time.time() - start_time) * 1000
            }
        )
        await chat_history.save()
        
        return ChatResponse(
            answer=response.content,
            references=references,
            metadata=ChatMetadata(
                tokens=response.usage.total_tokens,
                latency=(time.time() - start_time) * 1000
            )
        )
    
    @staticmethod
    async def list_chat_history(query: ChatHistoryQuery) -> Tuple[List[ChatHistory], int]:
        """
        获取对话历史列表
        
        Args:
            query: 查询参数
            
        Returns:
            对话历史列表和总数
        """
        filter_params = {}
        if query.kb_id:
            filter_params["kb_id"] = query.kb_id
        if query.start_time:
            filter_params["created_at__gte"] = query.start_time
        if query.end_time:
            filter_params["created_at__lte"] = query.end_time
            
        skip = (query.page - 1) * query.page_size
            
        histories = await ChatHistory.find(
            filter_params,
            skip=skip,
            limit=query.page_size,
            sort=[("-created_at", -1)]
        ).to_list()
        
        total = await ChatHistory.count(filter_params)
        
        return histories, total 