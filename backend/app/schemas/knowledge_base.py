"""
知识库相关的请求和响应Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class KnowledgeBaseCreate(BaseModel):
    """
    知识库创建请求
    """
    name: str = Field(..., description="知识库名称", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="知识库描述", max_length=200)
    tags: List[str] = Field(default_factory=list, description="标签列表")

class KnowledgeBaseUpdate(BaseModel):
    """
    知识库更新请求
    """
    name: Optional[str] = Field(None, description="知识库名称", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="知识库描述", max_length=200)
    tags: Optional[List[str]] = Field(None, description="标签列表")

class KnowledgeBaseQuery(BaseModel):
    """
    知识库查询参数
    """
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    keyword: Optional[str] = Field(None, description="搜索关键词")
    tags: Optional[List[str]] = Field(None, description="标签过滤") 