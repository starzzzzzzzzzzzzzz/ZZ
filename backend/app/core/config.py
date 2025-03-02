"""
应用配置
"""
from pathlib import Path
from typing import Optional, Any, List, Dict
import os
import sys
import locale
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

def setup_environment():
    """设置环境配置"""
    # 设置基础环境变量
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # 设置文件系统编码
    if sys.platform == 'darwin':  # macOS
        try:
            locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            except locale.Error:
                pass

# 初始化环境
setup_environment()

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理特殊类型"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, bytes):
            try:
                # 尝试多种编码方式
                encodings = ['utf-8', 'latin1', 'ascii', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        return obj.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 如果所有编码都失败，返回base64编码
                import base64
                return base64.b64encode(obj).decode('ascii')
            except Exception:
                # 最后的后备方案：返回十六进制字符串
                return obj.hex()
        elif isinstance(obj, Path):
            return str(obj)
        return super().default(obj)

class Settings(BaseSettings):
    """应用配置类
    
    配置说明：
    - PDF_MAX_FILE_SIZE: PDF文件大小限制，默认为10MB (10485760字节)
    """
    
    # 基础配置
    APP_NAME: str = "知识库系统"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True  # 开发环境默认开启调试模式
    
    # 路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BASE_DIR.parent  # 项目根目录
    DATA_DIR: Path = PROJECT_ROOT / "data"  # 统一数据目录
    VECTOR_STORE_DIR: Path = DATA_DIR / "vector_store"  # 向量存储目录
    UPLOAD_DIR: Path = DATA_DIR / "uploads"  # 文件上传目录
    MODEL_DIR: Path = PROJECT_ROOT / "models"  # 模型目录
    LOG_DIR: Path = PROJECT_ROOT / "logs"  # 日志目录
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Path = LOG_DIR / "app.log"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/prt_knowledge_base"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    
    # OpenAI配置
    OPENAI_API_KEY: str = "test-key"  # 默认使用测试key
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # 向量模型配置
    SENTENCE_TRANSFORMER_MODEL: str = "text2vec-base-chinese"  # 使用本地中文模型
    SENTENCE_TRANSFORMER_FALLBACK: str = "text2vec-base-chinese"  # 备用模型也使用本地模型
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_SEQ_LENGTH: int = 512  # 最大序列长度
    
    # ChromaDB配置
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_PERSIST_DIR: str = str(VECTOR_STORE_DIR / "chromadb")
    
    # LLM配置
    LLM_MODEL_PATH: Path = MODEL_DIR / "llama-2-7b-chat.gguf"
    LLM_MODEL_TYPE: str = "llama"  # 模型类型
    LLM_API_BASE: str = "http://127.0.0.1:1234/v1"  # LM Studio地址
    LLM_API_KEY: str = "not-needed"  # LM Studio不需要API Key
    LLM_MAX_TOKENS: int = 1500  # 限制生成长度
    LLM_TEMPERATURE: float = 0.3  # 降低随机性
    LLM_TOP_P: float = 0.85  # 适中的核采样阈值
    LLM_PRESENCE_PENALTY: float = 0.2  # 添加存在惩罚
    LLM_FREQUENCY_PENALTY: float = 0.2  # 添加频率惩罚
    LLM_CONTEXT_WINDOW: int = 4096
    
    # PDF处理配置
    PDF_CHUNK_SIZE: int = 1000
    PDF_CHUNK_OVERLAP: int = 200
    PDF_MAX_FILE_SIZE: int = 41943040  # 40MB = 40 * 1024 * 1024
    
    # 支持的模型列表
    SUPPORTED_MODELS: List[str] = ["chatglm3", "qwen", "llama2"]
    
    is_test: bool = False
    
    # 语义搜索配置
    SEMANTIC_SEARCH_CONFIG: Dict[str, Any] = {
        "vector_top_k": 5,      # 向量检索返回数量
        "keyword_top_k": 5,     # 关键词检索返回数量
        "score_threshold": 0.001,  # 相似度阈值
        "hybrid_weight": 0.7,    # 向量检索权重 (1-hybrid_weight 为关键词检索权重)
    }
    
    # 上下文构建配置
    CONTEXT_CONFIG: Dict[str, Any] = {
        "max_chunks": 5,           # 最大文档片段数
        "min_similarity": 0.6,     # 最小相似度阈值
        "min_tokens": 500,         # 最小上下文长度
        "max_tokens": 3000,        # 最大上下文长度
        "chunk_overlap": 50,       # 片段重叠阈值(%)
    }
    
    def __init__(self):
        super().__init__()
        # 确保日志目录存在
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件
        if not self.LOG_FILE.exists():
            self.LOG_FILE.touch()
            
        # 配置日志
        import logging
        
        # 移除已存在的处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # 配置日志
        logging.basicConfig(
            level=self.LOG_LEVEL,
            format=self.LOG_FORMAT,
            handlers=[
                logging.FileHandler(str(self.LOG_FILE), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def get_safe_path(self, path: Path) -> Path:
        """获取安全的路径（确保是ASCII编码）"""
        try:
            str(path).encode('ascii')
            return path
        except UnicodeEncodeError:
            # 如果包含非ASCII字符，使用hash值创建安全路径
            import hashlib
            safe_name = hashlib.md5(str(path).encode()).hexdigest()
            return path.parent / safe_name

    @property
    def safe_model_dir(self) -> Path:
        """获取安全的模型目录路径"""
        model_dir = self.get_safe_path(self.MODEL_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir

    @property
    def safe_upload_dir(self) -> Path:
        """获取安全的上传目录路径"""
        upload_dir = self.get_safe_path(self.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @property
    def safe_vector_store_dir(self) -> Path:
        """获取安全的向量存储目录路径"""
        vector_dir = self.get_safe_path(self.VECTOR_STORE_DIR)
        vector_dir.mkdir(parents=True, exist_ok=True)
        return vector_dir

settings = Settings()