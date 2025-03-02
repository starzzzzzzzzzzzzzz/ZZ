"""
知识库API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...db.session import get_db
from ...models.base import ResponseModel
from ...models.document import Document
from ...schemas.document import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBase
)
from ...services.knowledge_base_service import KnowledgeBaseService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库管理"])

@router.post("", response_model=ResponseModel)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        service = KnowledgeBaseService(db)
        kb = service.create_knowledge_base(kb_create)
        return ResponseModel(data=kb)
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=ResponseModel)
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取知识库列表"""
    try:
        service = KnowledgeBaseService(db)
        kbs, total = service.list_knowledge_bases(
            page=page,
            page_size=page_size,
            keyword=keyword
        )
        
        # 即使列表为空也返回正确的结构
        return ResponseModel(
            data={
                "items": kbs,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": total > page * page_size
            },
            message="获取知识库列表成功"
        )
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        # 返回空列表而不是抛出错误
        return ResponseModel(
            data={
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False
            },
            message="获取知识库列表失败，返回空列表"
        )

@router.get("/{kb_id}", response_model=ResponseModel)
async def get_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    try:
        service = KnowledgeBaseService(db)
        kb = service.get_knowledge_base(kb_id)
        if not kb:
            return ResponseModel(
                code=404,
                message="知识库不存在",
                data=None
            )
        return ResponseModel(data=kb)
    except Exception as e:
        logger.error(f"获取知识库详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{kb_id}", response_model=ResponseModel)
async def update_knowledge_base(
    kb_id: int,
    kb_update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """更新知识库"""
    try:
        service = KnowledgeBaseService(db)
        kb = service.update_knowledge_base(kb_id, kb_update)
        if not kb:
            return ResponseModel(
                code=404,
                message="知识库不存在",
                data=None
            )
        return ResponseModel(data=kb)
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{kb_id}", response_model=ResponseModel)
async def delete_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """删除知识库"""
    try:
        service = KnowledgeBaseService(db)
        success = service.delete_knowledge_base(kb_id)
        if not success:
            return ResponseModel(
                code=404,
                message="知识库不存在",
                data=None
            )
        return ResponseModel(
            code=200,
            message="删除成功",
            data=None
        )
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}", exc_info=True)
        return ResponseModel(
            code=500,
            message=f"删除知识库失败: {str(e)}",
            data=None
        ) 