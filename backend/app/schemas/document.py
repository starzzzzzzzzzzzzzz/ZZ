"""
文档相关的请求和响应Schema
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentMetadataSchema(BaseModel):
    """
    文档元数据Schema
    """
    source: Optional[str] = Field(None, description="文档来源")
    author: Optional[str] = Field(None, description="文档作者")
    tags: Dict[str, Any] = Field(default_factory=dict, description="标签列表")

class DocumentUpload(BaseModel):
    """
    文档上传请求
    """
    kb_id: int = Field(..., description="知识库ID")
    title: str = Field(..., description="文档标题", min_length=1, max_length=255)
    content: str = Field(..., description="文档内容", min_length=1)
    metadata: Optional[DocumentMetadataSchema] = Field(None, description="元数据")

class DocumentUpdate(BaseModel):
    """
    文档更新请求
    """
    title: Optional[str] = Field(None, description="文档标题", min_length=1, max_length=255)
    content: Optional[str] = Field(None, description="文档内容", min_length=1)
    metadata: Optional[DocumentMetadataSchema] = Field(None, description="元数据")

class DocumentQuery(BaseModel):
    """
    文档查询参数
    """
    kb_id: int = Field(..., description="知识库ID")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(10, description="每页数量", ge=1, le=100)
    keyword: Optional[str] = Field(None, description="搜索关键词")
    tags: Optional[List[str]] = Field(None, description="标签过滤")

class DocumentBase(BaseModel):
    """文档基础模型"""
    title: str = Field(..., description="文档标题", max_length=255)
    content: Optional[str] = Field(None, description="文档内容")
    file_path: Optional[str] = Field(None, description="文件路径", max_length=512)
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="MIME类型", max_length=100)

class DocumentCreate(DocumentBase):
    """创建文档模型"""
    pass

class DocumentUpdate(DocumentBase):
    """更新文档模型"""
    pass

class Document(DocumentBase):
    """文档模型"""
    id: int
    kb_id: int
    doc_meta: Optional[Dict[str, Any]] = Field(None, description="元数据")
    page_count: Optional[int] = Field(None, description="页数")
    vector_store_path: Optional[str] = Field(None, description="向量存储路径", max_length=512)
    chunk_count: Optional[int] = Field(0, description="分块数量")
    is_vectorized: Optional[bool] = Field(False, description="是否已向量化")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentChunk(BaseModel):
    """文档分块模型"""
    id: int
    document_id: int
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    chunk_metadata: Optional[Dict[str, Any]] = None
    vector_id: Optional[str] = Field(None, max_length=64)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PDFUploadResponse(BaseModel):
    """PDF上传响应"""
    success: bool
    error: Optional[str] = None
    document: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ChatResponse(BaseModel):
    """对话响应"""
    content: str
    references: Optional[List[Document]] = None

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="知识库描述")

class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, description="知识库名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="知识库描述")

class KnowledgeBase(BaseModel):
    """知识库模型"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: Optional[int] = Field(0, description="文档数量")

    class Config:
        from_attributes = True 