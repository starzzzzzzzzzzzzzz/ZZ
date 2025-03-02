"""
文档API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from ...models import KnowledgeBase  # 从models包中导入
from ...models.base import ResponseModel
from ...schemas.document import (
    DocumentUpload,
    DocumentUpdate,
    DocumentQuery,
    PDFUploadResponse,
    ChatResponse
)
from ...services.document_service import DocumentService
from ...services.knowledge_base_service import KnowledgeBaseService
from ...utils.pdf import extract_text_from_pdf
from ...core.config import settings
import logging
from sqlalchemy.orm import Session
from fastapi import Depends
from ...db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])

@router.post("/upload", response_model=ResponseModel)
async def upload_document(doc_upload: DocumentUpload):
    """
    上传普通文档
    """
    try:
        doc = await DocumentService.upload_document(doc_upload)
        return ResponseModel(data=doc.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pdf/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    request: Request,
    kb_id: int = Form(..., description="知识库ID"),
    title: str = Form(..., description="文档标题"),
    file: UploadFile = File(description="PDF文件")
):
    """上传PDF文档"""
    try:
        logger.info(f"接收到PDF上传请求: {file.filename}")
        logger.info(f"文件类型: {file.content_type}")
        logger.info(f"知识库ID: {kb_id}")
        
        if not hasattr(request.state, "db"):
            logger.error("数据库连接未初始化")
            return PDFUploadResponse(
                success=False,
                error="数据库连接未初始化"
            )
            
        # 验证知识库是否存在 - 只查询id
        kb = request.state.db.query(KnowledgeBase.id)\
            .filter(KnowledgeBase.id == kb_id)\
            .first()
        if not kb:
            logger.error(f"知识库不存在: {kb_id}")
            return PDFUploadResponse(
                success=False,
                error="知识库不存在"
            )
            
        logger.info("创建文档服务实例...")
        service = DocumentService(request.state.db)
        
        logger.info("开始处理PDF文档...")
        result = await service.create_pdf_document(
            file=file,
            kb_id=kb_id,
            title=title
        )
        
        if result["code"] != 200:
            logger.error(f"文档处理失败: {result['message']}")
            return PDFUploadResponse(
                success=False,
                error=result["message"]
            )
            
        logger.info(f"文档处理完成，ID: {result['data']['id']}")
        logger.info(f"返回数据: {result['data']}")
        
        return PDFUploadResponse(
            success=True,
            document={
                "id": result["data"]["id"],
                "kb_id": kb_id,
                "title": result["data"]["title"],
                "content": None,
                "file_path": result["data"].get("file_path"),
                "file_size": result["data"]["file_size"],
                "mime_type": result["data"].get("mime_type"),
                "page_count": result["data"]["page_count"],
                "vector_store_path": result["data"].get("vector_store_path"),
                "chunk_count": result["data"]["chunk_count"],
                "is_vectorized": result["data"]["is_vectorized"],
                "created_at": result["data"]["created_at"],
                "updated_at": result["data"].get("updated_at")
            }
        )
    except Exception as e:
        logger.error(f"PDF上传失败: {str(e)}", exc_info=True)
        return PDFUploadResponse(
            success=False,
            error=str(e)
        )

@router.get("/{doc_id}", response_model=ResponseModel)
async def get_document(
    doc_id: str,
    request: Request
):
    """
    获取文档信息
    """
    try:
        service = DocumentService(request.state.db)
        doc = service.get_document_dict(doc_id)  # 使用get_document_dict而不是get_document
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        return ResponseModel(data=doc)
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=ResponseModel)
async def list_documents(
    request: Request,
    kb_id: int,
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """获取文档列表"""
    try:
        logger.info(f"接收到文档列表请求: kb_id={kb_id}, page={page}, page_size={page_size}, keyword={keyword}")
        
        if not hasattr(request.state, "db"):
            logger.error("数据库连接未初始化")
            return ResponseModel(data={
                "total": 0,
                "items": []
            })
            
        service = DocumentService(request.state.db)
        docs, total = service.list_documents(
            kb_id=kb_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            tags=tags
        )
        
        logger.info(f"查询到文档总数: {total}")
        logger.info(f"当前页文档数量: {len(docs)}")
        if docs:
            logger.info(f"第一个文档: {docs[0]}")
        
        response_data = {
            "total": total,
            "items": docs
        }
        logger.info(f"返回数据: {response_data}")
        
        return ResponseModel(data=response_data)
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
        # 返回空列表而不是抛出错误
        return ResponseModel(data={
            "total": 0,
            "items": []
        })

@router.put("/{doc_id}", response_model=ResponseModel)
async def update_document(doc_id: str, doc_update: DocumentUpdate, request: Request):
    """
    更新文档信息
    """
    try:
        service = DocumentService(request.state.db)
        doc = service.update_document(
            doc_id=doc_id,
            title=doc_update.title,
            content=doc_update.content,
            doc_meta=doc_update.metadata.dict() if doc_update.metadata else None
        )
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
            
        # 转换为字典格式
        doc_dict = {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "metadata": doc.doc_meta.dict() if doc.doc_meta else {},
            "updated_at": doc.updated_at.isoformat()
        }
        return ResponseModel(data=doc_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}", response_model=ResponseModel)
async def delete_document(
    doc_id: int,
    request: Request
):
    """删除文档"""
    try:
        service = DocumentService(request.state.db)
        success = service.delete_document(doc_id)
        if not success:
            return ResponseModel(
                code=404,
                message="文档不存在",
                data=None
            )
        return ResponseModel(message="删除成功")
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pdf/{doc_id}/chat", response_model=ChatResponse)
async def chat_with_pdf(doc_id: str, question: str):
    """
    与PDF文档对话
    """
    try:
        response = await DocumentService.chat_with_document(doc_id, question)
        return response
    except Exception as e:
        logger.error(f"PDF对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ResponseModel)
async def chat_with_documents(
    request: Request,
    query: str
):
    """
    与文档进行对话
    """
    try:
        service = DocumentService(request.state.db)
        result = service.chat(query)
        return ResponseModel(data=result)
    except Exception as e:
        logger.error(f"文档对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vectorize", response_model=ResponseModel)
async def vectorize_all_documents(
    db: Session = Depends(get_db)
):
    """重新向量化所有文档"""
    try:
        service = DocumentService(db)
        result = await service.vectorize_all_documents()
        return ResponseModel(
            code=200,
            message="向量化完成" if result else "向量化失败",
            data={"success": result}
        )
    except Exception as e:
        logger.error(f"向量化文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=ResponseModel)
async def search_documents(
    request: Request,
    body: dict
):
    """搜索文档"""
    try:
        service = DocumentService(request.state.db)
        results = await service.search_similar_chunks(
            query=body.get("query"),
            top_k=body.get("top_k", 3)
        )
        return ResponseModel(data=results)
    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 