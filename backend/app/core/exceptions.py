"""
统一的异常处理模块
"""
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    """错误详情模型"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class BaseAppException(Exception):
    """应用基础异常"""
    def __init__(
        self,
        message: str,
        code: int = 500,
        sub_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.sub_code = sub_code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "sub_code": self.sub_code,
            "message": self.message,
            "details": self.details
        }

class ValidationException(BaseAppException):
    """数据验证异常"""
    def __init__(
        self,
        message: str,
        errors: List[ErrorDetail],
        code: int = 400
    ):
        super().__init__(
            message=message,
            code=code,
            sub_code="VALIDATION_ERROR",
            details={"errors": [error.dict() for error in errors]}
        )

class DocumentException(BaseAppException):
    """文档相关异常"""
    def __init__(
        self,
        message: str,
        doc_id: str,
        code: int = 400,
        sub_code: str = "DOCUMENT_ERROR"
    ):
        super().__init__(
            message=message,
            code=code,
            sub_code=sub_code,
            details={"doc_id": doc_id}
        )

class DocumentNotFoundError(DocumentException):
    """文档不存在异常"""
    def __init__(self, doc_id: str):
        super().__init__(
            message=f"Document not found: {doc_id}",
            doc_id=doc_id,
            code=404,
            sub_code="DOCUMENT_NOT_FOUND"
        )

class DocumentProcessError(DocumentException):
    """文档处理异常"""
    def __init__(self, doc_id: str, error_message: str):
        super().__init__(
            message=f"Failed to process document: {error_message}",
            doc_id=doc_id,
            code=500,
            sub_code="DOCUMENT_PROCESS_ERROR"
        )

class VectorStoreException(BaseAppException):
    """向量存储相关异常"""
    def __init__(
        self,
        message: str,
        code: int = 500,
        sub_code: str = "VECTOR_STORE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            sub_code=sub_code,
            details=details
        )

def handle_app_exception(exc: BaseAppException) -> HTTPException:
    """处理应用异常，转换为HTTP异常"""
    return HTTPException(
        status_code=exc.code,
        detail=exc.to_dict()
    ) 