"""API路由配置"""
from fastapi import APIRouter

from backend.app.api.endpoints import pdf

api_router = APIRouter()

# 添加PDF处理路由
api_router.include_router(pdf.router, prefix="/pdf", tags=["pdf"]) 