"""
聊天API路由
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
from datetime import datetime

from ...db.session import get_db
from ...models.chat import Chat, ChatMessage
from ...schemas.chat import ChatCreate, ChatMessageCreate, ChatResponse
from ...services.chat_service import ChatService
from ...utils.llm import llm_client
from ...utils.json import json_serial
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["对话"])

@router.post("", response_model=ChatResponse)
async def create_chat(
    chat_create: ChatCreate,
    db: Session = Depends(get_db)
):
    """创建新对话"""
    try:
        service = ChatService(db)
        chat = await service.create_chat(chat_create)
        return ChatResponse(data=chat)
    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=ChatResponse)
async def list_chats(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20
):
    """获取对话列表"""
    try:
        service = ChatService(db)
        chats = await service.list_chats(page, page_size)
        return ChatResponse(data=chats)
    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    db: Session = Depends(get_db)
):
    """获取对话详情"""
    try:
        service = ChatService(db)
        chat = await service.get_chat(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="对话不存在")
        return ChatResponse(data=chat)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{chat_id}", response_model=ChatResponse)
async def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db)
):
    """删除对话"""
    try:
        service = ChatService(db)
        success = await service.delete_chat(chat_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        return ChatResponse(message="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_response(generator):
    """流式响应生成器"""
    try:
        async for chunk in generator:
            if chunk:
                # 确保响应格式正确
                response = {
                    "data": chunk,
                    "error": False
                }
                yield f"data: {json.dumps(response, default=json_serial, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"流式响应出错: {str(e)}")
        error_response = {
            "error": True,
            "message": str(e)
        }
        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"

@router.post("/{chat_id}/messages")
@router.get("/{chat_id}/messages")
async def add_message(
    chat_id: int,
    content: str = None,
    message: ChatMessageCreate = None,
    stream: bool = False,
    db: Session = Depends(get_db)
):
    """发送消息"""
    try:
        service = ChatService(db)
        
        # 如果是GET请求，从查询参数构建消息
        if content and not message:
            message = ChatMessageCreate(content=content)
        
        if not message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        if stream:
            # 流式响应
            generator = service.add_message_stream(chat_id, message)
            return StreamingResponse(
                stream_response(generator),
                media_type="text/event-stream"
            )
        else:
            # 普通响应
            messages = await service.add_message(chat_id, message)
            return ChatResponse(data=messages)
            
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simple", response_model=ChatResponse)
async def simple_chat(
    message: ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """简单对话接口"""
    try:
        service = ChatService(db)
        # 创建一个临时对话
        chat_create = ChatCreate(title="临时对话")
        chat_dict = await service.create_chat(chat_create)
        # 使用完整的知识库服务处理消息
        response = await service.add_message(chat_dict["id"], message)
        return ChatResponse(data=response)
    except Exception as e:
        logger.error(f"简单对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 