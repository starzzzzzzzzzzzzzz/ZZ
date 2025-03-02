class BaseError(Exception):
    """基础错误类"""
    def __init__(self, message: str = "未知错误"):
        self.message = message
        super().__init__(self.message)

class NotFoundError(BaseError):
    """资源未找到错误"""
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message)

class ValidationError(BaseError):
    """数据验证错误"""
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message)

class DatabaseError(BaseError):
    """数据库操作错误"""
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message)

class FileProcessError(BaseError):
    """文件处理错误"""
    def __init__(self, message: str = "文件处理失败"):
        super().__init__(message)

class LLMError(BaseError):
    """LLM 调用错误"""
    def __init__(self, message: str = "LLM 调用失败"):
        super().__init__(message)

class VectorStoreError(BaseError):
    """向量存储错误"""
    def __init__(self, message: str = "向量存储操作失败"):
        super().__init__(message) 