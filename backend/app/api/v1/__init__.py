"""
API路由模块
"""
from fastapi import APIRouter
from .document import router as document_router
from .chat import router as chat_router
from .knowledge_base import router as knowledge_base_router

api_router = APIRouter()

api_router.include_router(document_router)
api_router.include_router(chat_router)
api_router.include_router(knowledge_base_router) 