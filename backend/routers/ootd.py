# routers/ootd.py - 简化版本（无JWT认证）
import os
import uuid
import aiofiles
import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from langchain.schema import HumanMessage, AIMessage

from models.database_models import User, ConversationMessage, OOTDSession, MessageType, MessageRole
from models.ootd_models import (
    OOTDChatRequest, OOTDChatResponse, MessageCreate, MessageResponse,
    ConversationCreate, ConversationResponse, FileUploadRequest
)
from models.user_models import StandardResponse
from agents.enhanced_ootd_agent import get_enhanced_ootd_agent

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ootd", tags=["OOTD助手"])

# 创建必要的目录
def ensure_directories():
    """确保所需目录存在"""
    base_dir = "user_data/advice_based_on_userdata"
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

async def get_user_by_id(user_id: int) -> User:
    """通过用户ID获取用户，简化版认证"""
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户ID {user_id} 不存在"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return user

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(conversation_data: ConversationCreate):
    """创建新对话"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(conversation_data.user_id)
        
        # 创建会话
        session = await OOTDSession.create(
            user_id=conversation_data.user_id,
            session_id=str(uuid.uuid4()),
            title=conversation_data.title or f"OOTD对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            user_preferences=conversation_data.user_preferences
        )
        
        # 创建用户数据目录
        user_dir = os.path.join(ensure_directories(), str(conversation_data.user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        logger.info(f"创建新OOTD对话: user_id={conversation_data.user_id}, session_id={session.session_id}")
        
        return ConversationResponse(**session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建对话失败"
        )

@router.post("/chat", response_model=OOTDChatResponse)
async def chat_with_ootd_assistant(request: OOTDChatRequest):
    """与OOTD助手聊天"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(request.user_id)
        
        # 获取或创建会话
        if request.conversation_id:
            session = await OOTDSession.get_or_none(session_id=request.conversation_id, user_id=request.user_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="对话不存在"
                )
        else:
            # 创建新会话
            session = await OOTDSession.create(
                user_id=request.user_id,
                session_id=str(uuid.uuid4()),
                title=f"OOTD对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        # 保存用户消息
        user_message = await ConversationMessage.create(
            user_id=request.user_id,
            message_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content_type=MessageType.TEXT,
            text_content=request.message,
            conversation_id=session.session_id,
            sequence_number=session.message_count + 1
        )
        
        # 获取对话历史（如果需要上下文）
        chat_history = []
        if request.include_recent_context:
            recent_messages = await ConversationMessage.get_conversation_history(
                request.user_id, session.session_id, limit=20
            )
            
            for msg in recent_messages:
                if msg.role == MessageRole.USER:
                    chat_history.append(HumanMessage(content=msg.text_content))
                elif msg.role == MessageRole.ASSISTANT:
                    chat_history.append(AIMessage(content=msg.text_content))
        
        # 与AI助手交互
        agent = get_enhanced_ootd_agent()
        result = await agent.chat(
            user_id=request.user_id,
            message=request.message,
            chat_history=chat_history,
            page_context=request.page_context
        )
        
        # 保存助手回复
        assistant_message_id = str(uuid.uuid4())
        assistant_message = await ConversationMessage.create(
            user_id=request.user_id,
            message_id=assistant_message_id,
            role=MessageRole.ASSISTANT,
            content_type=MessageType.TEXT,
            text_content=result["response"],
            conversation_id=session.session_id,
            sequence_number=session.message_count + 2,
            is_processed=True,
            processing_result={
                "user_data_used": result["user_data_used"],
                "intermediate_steps": len(result.get("intermediate_steps", []))
            }
        )
        
        # 更新会话信息
        session.message_count += 2
        session.last_message_at = datetime.now(timezone.utc)
        await session.save()
        
        # 保存对话到文件（可选）
        await save_conversation_to_file(request.user_id, session.session_id, user_message, assistant_message)
        
        logger.info(f"OOTD聊天完成: user_id={request.user_id}, session_id={session.session_id}")
        
        return OOTDChatResponse(
            success=True,
            conversation_id=session.session_id,
            response=result["response"],
            user_data_used=result["user_data_used"],
            message_id=assistant_message_id,
            created_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OOTD聊天失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败: {str(e)}"
        )

@router.post("/upload-file", response_model=StandardResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: int = None,
    conversation_id: str = None,
    file_type: str = "image",
    description: str = None
):
    """上传文件到对话中"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(user_id)
        
        # 验证会话存在
        session = await OOTDSession.get_or_none(session_id=conversation_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 验证文件类型
        allowed_types = {
            "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
            "video": ["video/mp4", "video/avi", "video/mov"],
            "audio": ["audio/mp3", "audio/wav", "audio/m4a"]
        }
        
        if file_type not in allowed_types or file.content_type not in allowed_types[file_type]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 创建用户文件目录
        user_dir = os.path.join(ensure_directories(), str(user_id), "files")
        os.makedirs(user_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{timestamp}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(user_dir, filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 保存文件记录到数据库
        file_message = await ConversationMessage.create(
            user_id=user_id,
            message_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content_type=getattr(MessageType, file_type.upper()),
            text_content=description,
            file_path=file_path,
            metadata={
                "original_filename": file.filename,
                "file_size": len(content),
                "content_type": file.content_type
            },
            conversation_id=conversation_id,
            sequence_number=session.message_count + 1
        )
        
        # 更新会话
        await session.add_message_count()
        
        logger.info(f"文件上传成功: user_id={user_id}, file={filename}")
        
        return StandardResponse(
            success=True,
            message="文件上传成功",
            data={
                "message_id": file_message.message_id,
                "filename": filename,
                "file_path": file_path
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败"
        )

@router.get("/conversations/{conversation_id}/history", response_model=List[MessageResponse])
async def get_conversation_history(
    conversation_id: str,
    user_id: int,
    limit: int = 50
):
    """获取对话历史"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(user_id)
        
        # 验证会话属于当前用户
        session = await OOTDSession.get_or_none(session_id=conversation_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 获取消息历史
        messages = await ConversationMessage.get_conversation_history(
            user_id, conversation_id, limit
        )
        
        return [MessageResponse(**msg.to_dict()) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话历史失败"
        )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: int,
    limit: int = 20
):
    """获取用户的所有对话"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(user_id)
        
        sessions = await OOTDSession.filter(
            user_id=user_id,
            is_active=True
        ).order_by("-updated_at").limit(limit)
        
        return [ConversationResponse(**session.to_dict()) for session in sessions]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话列表失败"
        )

@router.get("/files/{user_id}/{filename}")
async def get_file(user_id: int, filename: str):
    """获取上传的文件"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(user_id)
        
        # 构建文件路径
        file_path = os.path.join(ensure_directories(), str(user_id), "files", filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 安全检查：防止路径遍历攻击
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名"
            )
        
        # 验证文件扩展名安全性
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.avi', '.mov', '.mp3', '.wav', '.m4a'}
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件格式"
            )
        
        return FileResponse(file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件失败"
        )

async def save_conversation_to_file(user_id: int, conversation_id: str, user_message, assistant_message):
    """保存对话到本地文件"""
    try:
        user_dir = os.path.join(ensure_directories(), str(user_id))
        conversation_file = os.path.join(user_dir, f"conversation_{conversation_id}.jsonl")
        
        # 准备对话数据
        conversation_data = [
            {
                "timestamp": user_message.created_at.isoformat(),
                "role": user_message.role,
                "content": user_message.text_content,
                "message_id": user_message.message_id
            },
            {
                "timestamp": assistant_message.created_at.isoformat(),
                "role": assistant_message.role,
                "content": assistant_message.text_content,
                "message_id": assistant_message.message_id
            }
        ]
        
        # 追加到文件
        async with aiofiles.open(conversation_file, 'a', encoding='utf-8') as f:
            for data in conversation_data:
                await f.write(json.dumps(data, ensure_ascii=False) + '\n')
                
    except Exception as e:
        logger.warning(f"保存对话文件失败: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: int):
    """删除对话（软删除）"""
    try:
        # 验证用户是否存在
        user = await get_user_by_id(user_id)
        
        session = await OOTDSession.get_or_none(session_id=conversation_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        session.is_active = False
        await session.save()
        
        return StandardResponse(
            success=True,
            message="对话删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除对话失败"
        )

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "ootd-assistant"}

@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: int):
    """获取用户基本信息（简化版）"""
    try:
        user = await get_user_by_id(user_id)
        return {
            "success": True,
            "user_info": user.to_dict(),
            "message": f"用户 {user.nickname or user_id} 的信息"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )