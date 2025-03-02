"""PDF相关的数据模型"""
from typing import List, Optional
from pydantic import BaseModel

class PDFMetadata(BaseModel):
    """PDF元数据模型"""
    title: str = "未知标题"
    author: str = "未知作者"
    subject: Optional[str] = None
    keywords: List[str] = []
    creator: Optional[str] = None
    producer: Optional[str] = None
    page_count: int = 0
    file_size: int = 0
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None

class PDFSection(BaseModel):
    """PDF文档章节模型"""
    title: str
    level: int
    page_number: int
    content: str

class PDFContent(BaseModel):
    """PDF内容模型"""
    metadata: PDFMetadata
    sections: List[str]
    full_text: str
    file_path: str
    success: bool = True
    error: Optional[str] = None 