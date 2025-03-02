"""
ID生成器工具类
"""
import uuid
import time
import base64
import hashlib
from typing import Optional

class IDGenerator:
    """ID生成器类，用于生成各种格式的唯一标识符"""
    
    @staticmethod
    def generate_uuid() -> str:
        """生成UUID
        
        Returns:
            UUID字符串
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_short_uuid() -> str:
        """生成短UUID（16位）
        
        Returns:
            短UUID字符串
        """
        # 生成UUID并移除连字符
        uuid_str = str(uuid.uuid4()).replace('-', '')
        # 取前16位
        return uuid_str[:16]
    
    @staticmethod
    def generate_timestamp_id() -> str:
        """生成基于时间戳的ID
        
        Returns:
            时间戳ID字符串
        """
        # 获取当前时间戳（毫秒）
        timestamp = int(time.time() * 1000)
        # 添加4位随机数
        random_num = uuid.uuid4().int % 10000
        return f"{timestamp}{random_num:04d}"
    
    @staticmethod
    def generate_base64_id(prefix: Optional[str] = None) -> str:
        """生成base64编码的ID
        
        Args:
            prefix: ID前缀
            
        Returns:
            base64编码的ID字符串
        """
        # 生成UUID
        uuid_bytes = uuid.uuid4().bytes
        # base64编码
        base64_id = base64.urlsafe_b64encode(uuid_bytes).decode('ascii').rstrip('=')
        # 添加前缀
        if prefix:
            return f"{prefix}_{base64_id}"
        return base64_id
    
    @staticmethod
    def generate_hash_id(content: str, length: int = 16) -> str:
        """根据内容生成哈希ID
        
        Args:
            content: 用于生成哈希的内容
            length: ID长度
            
        Returns:
            哈希ID字符串
        """
        # 使用MD5生成哈希
        hash_obj = hashlib.md5(content.encode())
        # 截取指定长度
        return hash_obj.hexdigest()[:length] 