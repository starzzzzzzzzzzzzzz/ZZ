from typing import Any, Generic, Optional, TypeVar, List
from pydantic import BaseModel

DataT = TypeVar('DataT')

class BaseResponse(BaseModel, Generic[DataT]):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[DataT] = None

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

class ListResponse(BaseModel, Generic[DataT]):
    """列表响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: List[DataT] = []
    total: int = 0
    page: Optional[int] = None
    page_size: Optional[int] = None 