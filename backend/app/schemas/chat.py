"""
聊天相关的请求和响应Schema
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from ..models.base import ResponseModel

class ChatMessageBase(BaseModel):
    """消息基础模型"""
    content: str = Field(..., description="消息内容")

class ChatMessageCreate(ChatMessageBase):
    """创建消息请求"""
    pass

class ChatMessageReference(BaseModel):
    """消息引用模型"""
    doc_id: int = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="引用内容")
    score: float = Field(..., description="相似度分数")

class ChatMessage(ChatMessageBase):
    """消息模型"""
    id: int
    chat_id: int
    role: str = Field(..., description="角色(user/assistant)")
    references: Optional[List[ChatMessageReference]] = Field(None, description="引用信息")
    created_at: datetime

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    """对话基础模型"""
    title: Optional[str] = Field(None, description="对话标题")

class ChatCreate(ChatBase):
    """创建对话请求"""
    pass

class Chat(ChatBase):
    """对话模型"""
    id: int
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChatResponse(ResponseModel):
    """对话响应模型"""
    data: Optional[Any] = Field(None, description="响应数据")

class SearchParams(BaseModel):
    """
    搜索参数Schema
    """
    top_k: int = Field(default=3, description="返回结果数量", ge=1, le=10)
    score_threshold: float = Field(default=0.6, description="相似度阈值", ge=0, le=1)

class ChatQuery(BaseModel):
    """
    对话查询请求
    """
    kb_id: str = Field(..., description="知识库ID")
    query: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="对话历史")
    search_params: Optional[SearchParams] = Field(None, description="搜索参数")

class Reference(BaseModel):
    """
    引用来源Schema
    """
    doc_id: str = Field(..., description="文档ID")
    doc_title: str = Field(..., description="文档标题")
    content: str = Field(..., description="相关内容片段")
    score: float = Field(..., description="相关度分数")

class ChatMetadata(BaseModel):
    """
    对话元数据Schema
    """
    tokens: int = Field(..., description="token数量")
    latency: float = Field(..., description="响应时间(ms)")

class ChatHistoryQuery(BaseModel):
    """
    对话历史查询参数
    """
    kb_id: Optional[str] = Field(None, description="知识库ID")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间") 