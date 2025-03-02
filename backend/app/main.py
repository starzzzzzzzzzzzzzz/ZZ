"""
主应用入口文件
"""
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder, ENCODERS_BY_TYPE
from fastapi.exceptions import RequestValidationError
import traceback
from pathlib import Path
import base64
import logging
from sqlalchemy.orm import Session

from .core.config import settings, CustomJSONEncoder
from .api.v1 import api_router
from .db.session import get_db

# 配置日志记录
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 如果是调试模式，添加文件处理器
if settings.DEBUG:
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def safe_bytes_encoder(obj: bytes) -> str:
    """安全的字节编码器"""
    if len(obj) < 1024 * 1024:  # 1MB以下的数据
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # 尝试其他编码
                for encoding in ['gbk', 'gb2312', 'latin1']:
                    try:
                        return obj.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 如果都失败，使用base64
                import base64
                return base64.b64encode(obj).decode('ascii')
            except Exception:
                return f"<binary data: {len(obj)} bytes>"
    return f"<binary data: {len(obj)} bytes>"

# 替换默认的字节编码器
ENCODERS_BY_TYPE[bytes] = safe_bytes_encoder

app = FastAPI(
    title=settings.APP_NAME,
    description="基于大语言模型的智能知识库系统",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
    expose_headers=["*"]  # 暴露所有头部
)

# 配置自定义JSON编码器
app.json_encoder = CustomJSONEncoder

# 添加数据库会话中间件
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """数据库会话中间件"""
    try:
        request.state.db = next(get_db())
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"数据库会话中间件错误: {str(e)}")
        raise
    finally:
        if hasattr(request.state, "db"):
            request.state.db.close()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    debug_info = {
        "exception_type": exc.__class__.__name__,
        "exception_msg": str(exc),
        "traceback": traceback.format_exc()
    } if settings.DEBUG else None
    
    content = {
        "detail": str(exc),
        "error_type": exc.__class__.__name__
    }
    
    if debug_info and settings.DEBUG:
        content["debug_info"] = debug_info
        
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证错误"""
    logger.info("=== 请求验证错误 ===")
    logger.info(f"错误详情: {exc.errors()}")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求URL: {request.url}")
    
    # 只记录关键的请求头信息
    headers = {
        'content-type': request.headers.get('content-type', ''),
        'content-length': request.headers.get('content-length', ''),
        'user-agent': request.headers.get('user-agent', '')
    }
    logger.info(f"关键请求头: {headers}")
    
    # 对于文件上传，只记录文件信息而不是内容
    if request.headers.get('content-type', '').startswith('multipart/form-data'):
        form = await request.form()
        file_info = {}
        for key, value in form.items():
            if hasattr(value, 'filename'):
                file_info[key] = {
                    'filename': value.filename,
                    'content_type': value.content_type,
                    'size': value.size
                }
        logger.info(f"上传的文件信息: {file_info}")
    
    errors = []
    for error in exc.errors():
        error_dict = {
            'loc': error.get('loc', []),
            'msg': error.get('msg', ''),
            'type': error.get('type', '')
        }
        errors.append(error_dict)
    
    if request.url.path.startswith("/api/v1/pdf"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "metadata": {
                    "title": "",
                    "author": "",
                    "page_count": 0,
                    "file_size": 0,
                    "creation_date": None,
                    "modification_date": None
                },
                "sections": [],
                "full_text": "",
                "success": False,
                "error": "请求验证失败",
                "detail": errors
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": errors,
                "error_type": "ValidationError"
            }
        )

# 注册路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """
    根路由，用于健康检查
    """
    return {"status": "ok", "message": f"{settings.APP_NAME}服务正常运行"} 