# models/ootd_models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from models.database_models import MessageType, MessageRole  # 导入枚举，避免重复定义

class MessageCreate(BaseModel):
    """创建消息的请求模型"""
    user_id: int = Field(..., description="用户ID")
    conversation_id: str = Field(..., description="对话ID")
    role: MessageRole = Field(..., description="消息角色")
    content_type: MessageType = Field(..., description="内容类型")
    text_content: Optional[str] = Field(None, description="文本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: int
    message_id: str
    role: MessageRole
    content_type: MessageType
    text_content: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    conversation_id: str
    sequence_number: int
    created_at: Optional[datetime] = None
    is_processed: bool = False

class ConversationCreate(BaseModel):
    """创建对话的请求模型"""
    user_id: int = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="对话标题")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")

class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: int
    session_id: str
    user_id: int
    title: Optional[str] = None
    is_active: bool
    message_count: int
    user_preferences: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None

class OOTDChatRequest(BaseModel):
    """OOTD聊天请求模型"""
    user_id: int = Field(..., description="用户ID")
    conversation_id: Optional[str] = Field(None, description="对话ID，不提供则创建新对话")
    message: str = Field(..., description="用户消息")
    page_context: Optional[str] = Field(None, description="页面上下文：home, style_analysis, wardrobe, profile")
    include_user_data: bool = Field(True, description="是否包含用户个人数据")
    include_recent_context: bool = Field(True, description="是否包含最近对话上下文")

class OOTDChatResponse(BaseModel):
    """OOTD聊天响应模型"""
    success: bool
    conversation_id: str
    response: str
    recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="具体推荐列表")
    user_data_used: bool = Field(False, description="是否使用了用户数据")
    message_id: str
    created_at: datetime

class FileUploadRequest(BaseModel):
    """文件上传请求模型"""
    user_id: int = Field(..., description="用户ID") 
    conversation_id: str = Field(..., description="对话ID")
    file_type: MessageType = Field(..., description="文件类型")
    description: Optional[str] = Field(None, description="文件描述")

class UserDataSummary(BaseModel):
    """用户数据摘要模型"""
    user_profile: Dict[str, Any]
    wardrobe_summary: Dict[str, Any]
    recent_preferences: Optional[Dict[str, Any]] = None

class OOTDRecommendation(BaseModel):
    """OOTD推荐模型"""
    outfit_id: str
    items: List[Dict[str, Any]]
    occasion: Optional[str] = None
    weather_appropriate: Optional[bool] = None
    style_tags: List[str] = []
    confidence_score: float
    reasoning: str