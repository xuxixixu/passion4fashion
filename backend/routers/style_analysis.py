import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comprehensive_style_analyzer import ComprehensiveStyleAnalyzer, ImageValidationError
from personalized_response_generator import PersonalizedResponseGenerator
from avatar_generator import AvatarGenerator
from doubao_client import DoubaoClient
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime
import logging
import re
import json
from enum import Enum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/style", tags=["风格分析"])

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"      # 等待处理
    RUNNING = "running"      # 正在处理
    COMPLETED = "completed"  # 处理完成

# 全局任务状态存储（生产环境建议使用Redis）
task_storage: Dict[str, Dict[str, Any]] = {}

# 全局分析器实例
analyzer = None
response_generator = None
avatar_generator = None

async def get_analyzer():
    global analyzer
    if analyzer is None:
        client = DoubaoClient()
        analyzer = ComprehensiveStyleAnalyzer(client)
    return analyzer

async def get_response_generator():
    global response_generator
    if response_generator is None:
        client = DoubaoClient()
        response_generator = PersonalizedResponseGenerator(client)
    return response_generator

async def get_avatar_generator():
    global avatar_generator
    if avatar_generator is None:
        client = DoubaoClient()
        avatar_generator = AvatarGenerator(client)
    return avatar_generator

class StyleAnalysisRequest(BaseModel):
    style_image_names: Optional[List[str]] = None  # 喜欢的别人图片文件名
    user_image_names: Optional[List[str]] = None  # 自己的图片文件名
    text_requirements: Optional[str] = None
    user_name: Optional[str] = None  # 新增：用户昵称，用于个性化回复
    generate_avatar: Optional[bool] = True  # 新增：是否生成卡通头像
    page_session_id: Optional[str] = None  # 新增：页面级session_id

class TaskInitResponse(BaseModel):
    success: bool
    task_id: str
    status: TaskStatus
    message: str
    check_url: str  # 轮询状态的URL

class TaskStatusResponse(BaseModel):
    success: bool
    task_id: str
    status: TaskStatus
    progress: Optional[str] = None  # 当前进度描述
    result: Optional[Dict[str, Any]] = None  # 完成时的结果
    error_message: Optional[str] = None  # 错误信息
    message: str

class PersonalizedStyleResponse(BaseModel):
    success: bool
    content: str  # 直接的个性化回复文本
    metadata: dict  # 包含session_id、生成时间等元数据
    avatar_info: Optional[dict] = None  # 头像生成信息
    raw_analysis: Optional[dict] = None  # 可选：原始分析数据（调试用）
    message: str

def extract_page_session_from_filename(filename: str) -> tuple[str, str]:
    """
    从文件名中提取页面session_id
    
    Args:
        filename: 带前缀的文件名，如 "page_123456_1.jpg"
        
    Returns:
        tuple: (page_session_id, original_filename)
    """
    # 匹配 page_xxxxx_ 格式的前缀
    match = re.match(r'^(page_[^_]+_[^_]+)_(.+)$', filename)
    if match:
        page_session_id = match.group(1)
        original_filename = match.group(2)
        return page_session_id, original_filename
    else:
        # 如果没有匹配到前缀，返回原文件名
        logger.warning(f"文件名 {filename} 没有找到页面session_id前缀")
        return None, filename

def save_task_status(task_id: str, status: TaskStatus, **kwargs):
    """保存任务状态到存储中"""
    if task_id not in task_storage:
        task_storage[task_id] = {
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
        }
    
    task_storage[task_id]["status"] = status
    task_storage[task_id]["updated_at"] = datetime.now().isoformat()
    
    # 更新其他字段
    for key, value in kwargs.items():
        task_storage[task_id][key] = value
    
    logger.info(f"任务 {task_id} 状态更新为 {status}")

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """从存储中获取任务状态"""
    return task_storage.get(task_id)

async def process_style_analysis_task(task_id: str, request: StyleAnalysisRequest):
    """
    异步处理风格分析任务的后台函数
    """
    try:
        # 更新任务状态为运行中
        save_task_status(task_id, TaskStatus.RUNNING, progress="开始处理任务...")
        
        # 验证输入
        if not any([request.style_image_names, request.user_image_names, request.text_requirements]):
            # 使用COMPLETED状态，但返回错误结果
            error_result = {
                "success": False,
                "content": "请至少提供一种输入类型：风格图片、用户照片或文字需求。",
                "metadata": {
                    "error_type": "invalid_input",
                    "timestamp": datetime.now().isoformat()
                },
                "message": "输入验证失败"
            }
            save_task_status(task_id, TaskStatus.COMPLETED, result=error_result, progress="输入验证失败")
            return
        
        # 只有当有图片需求时才验证page_session_id
        has_images = bool(request.style_image_names or request.user_image_names)
        if has_images and not request.page_session_id:
            error_result = {
                "success": False,
                "content": "上传了图片但缺少页面session_id，无法定位图片文件。请重新上传图片。",
                "metadata": {
                    "error_type": "missing_session_id",
                    "timestamp": datetime.now().isoformat()
                },
                "message": "缺少必要参数"
            }
            save_task_status(task_id, TaskStatus.COMPLETED, result=error_result, progress="缺少页面session_id")
            return
        
        # 更新进度
        save_task_status(task_id, TaskStatus.RUNNING, progress="🔍 正在准备分析环境...")
        
        # 获取分析器实例
        analyzer = await get_analyzer()
        response_generator = await get_response_generator()
        
        # 构建本地文件路径 - 如果有页面session_id则使用，否则生成临时ID
        page_session_id = request.page_session_id or f"temp_{str(uuid.uuid4())[:8]}"
        base_path = os.path.join("/root/fashion/user_data", page_session_id)
        
        style_image_paths = None
        user_image_paths = None
        
        # 更新进度
        save_task_status(task_id, TaskStatus.RUNNING, progress="🔍 正在验证图片文件...")
        
        if request.style_image_names:
            style_image_paths = [
                os.path.join(base_path, "love", name) 
                for name in request.style_image_names
            ]
            # 验证文件存在
            for path in style_image_paths:
                if not os.path.exists(path):
                    error_result = {
                        "success": False,
                        "content": f"风格图片文件不存在，请重新上传图片。",
                        "metadata": {
                            "error_type": "file_not_found",
                            "missing_file": path,
                            "timestamp": datetime.now().isoformat()
                        },
                        "message": "文件不存在"
                    }
                    save_task_status(task_id, TaskStatus.COMPLETED, result=error_result, progress="风格图片文件不存在")
                    return
        
        if request.user_image_names:
            user_image_paths = [
                os.path.join(base_path, "self", name) 
                for name in request.user_image_names
            ]
            # 验证文件存在
            for path in user_image_paths:
                if not os.path.exists(path):
                    error_result = {
                        "success": False,
                        "content": f"用户图片文件不存在，请重新上传图片。",
                        "metadata": {
                            "error_type": "file_not_found",
                            "missing_file": path,
                            "timestamp": datetime.now().isoformat()
                        },
                        "message": "文件不存在"
                    }
                    save_task_status(task_id, TaskStatus.COMPLETED, result=error_result, progress="用户图片文件不存在")
                    return
        
        # Step 1: 执行综合分析（包含图片内容验证）
        save_task_status(task_id, TaskStatus.RUNNING, progress="🤖 AI正在深度分析你的风格特点...")
        logger.info(f"开始为页面会话 {page_session_id} 执行综合分析")
        
        try:
            analysis_result = await analyzer.analyze_comprehensive(
                style_image_paths=style_image_paths,
                user_image_paths=user_image_paths,
                text_requirements=request.text_requirements,
                session_id=page_session_id  # 使用页面session_id
            )
        except ImageValidationError as e:
            # 图片验证失败，返回友好的错误信息，但使用COMPLETED状态
            error_message = f"图片内容验证失败：{str(e)}"
            if "风景图片" in str(e) or "食物图片" in str(e):
                error_message = "检测到您上传的图片可能不包含服装或人物信息。请上传包含穿搭展示或个人照片的图片，以便我们为您提供准确的时尚建议。"
            elif "无人物" in str(e):
                error_message = "检测到您上传的个人照片中可能没有清晰的人物形象。请上传包含您本人清晰可见的照片，以便分析个人特征。"
            
            # 生成友好的错误回复
            response_generator = await get_response_generator()
            error_response = await response_generator.generate_image_validation_error_response(
                error_details={"error": str(e)},
                user_name=request.user_name
            )
            
            # 使用COMPLETED状态，但success=False表示失败
            error_result = {
                "success": False,
                "content": error_response["content"],
                "metadata": {
                    "error_type": "image_validation_failed",
                    "original_error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "user_name": request.user_name
                },
                "avatar_info": {"status": "disabled", "message": "图片验证失败，无法生成头像"},
                "message": "图片内容验证失败"
            }
            
            save_task_status(
                task_id, 
                TaskStatus.COMPLETED,  # 使用COMPLETED而不是ERROR
                result=error_result,
                progress="❌ 图片内容验证失败"
            )
            return
        except Exception as e:
            # 其他分析错误
            logger.error(f"综合分析失败: {str(e)}")
            
            error_result = {
                "success": False,
                "content": f"分析过程中出现了技术问题，请稍后重试。如果问题持续存在，请联系客服。",
                "metadata": {
                    "error_type": "analysis_failed", 
                    "timestamp": datetime.now().isoformat(),
                    "technical_error": str(e)
                },
                "avatar_info": {"status": "disabled", "message": "分析失败，无法生成头像"},
                "message": "分析过程出现错误"
            }
            
            save_task_status(
                task_id, 
                TaskStatus.COMPLETED,  # 使用COMPLETED而不是ERROR
                result=error_result,
                progress="❌ 分析过程出现错误"
            )
            return
        
        # Step 2: 生成个性化回复
        save_task_status(task_id, TaskStatus.RUNNING, progress="✨ 正在为你生成专属时尚建议...")
        logger.info(f"开始为页面会话 {page_session_id} 生成个性化回复")
        
        personalized_response = await response_generator.generate_personalized_response(
            analysis_result=analysis_result,
            user_name=request.user_name
        )
        
        # 构建基础响应数据
        response_data = {
            "success": True,
            "content": personalized_response["content"],  # 直接的文本内容
            "metadata": {
                "page_session_id": page_session_id,
                "timestamp": datetime.now().isoformat(),
                "analysis_confidence": personalized_response.get("analysis_confidence", 0.7),
                "user_name": request.user_name,
                "generated_at": personalized_response.get("generated_at")
            },
            "avatar_info": {"status": "disabled", "message": "用户未启用头像生成"},
            "message": "分析完成，已生成个性化建议"
        }
        
        # Step 3: 生成专属头像（如果用户选择了）
        if request.generate_avatar and user_image_paths:
            try:
                save_task_status(task_id, TaskStatus.RUNNING, progress="🎨 正在为你生成专属卡通头像...")
                avatar_generator = await get_avatar_generator()
                
                logger.info(f"开始为页面会话 {page_session_id} 生成专属头像")
                
                # 同步等待头像生成完成
                avatar_result = await avatar_generator.generate_styled_avatar(
                    analysis_result=analysis_result,
                    user_image_paths=user_image_paths,
                    session_id=page_session_id  # 使用页面session_id
                )
                
                # 根据头像生成结果更新响应数据
                if avatar_result.get("success", False) and avatar_result.get("avatar_path"):
                    # 头像生成成功
                    avatar_filename = os.path.basename(avatar_result["avatar_path"])
                    response_data["avatar_info"] = {
                        "status": "completed",
                        "message": "专属头像生成完成",
                        "avatar_url": f"http://123.60.11.207/api/style/avatars/{avatar_filename}",
                        "avatar_filename": avatar_filename,
                        "file_size": avatar_result.get("file_size", 0),
                        "generated_at": avatar_result.get("generated_at"),
                        "model": avatar_result.get("model", "doubao-seedream-3-0-t2i-250415")
                    }
                    
                    # 如果是占位符头像，添加说明
                    if avatar_result.get("is_placeholder", False):
                        response_data["avatar_info"]["is_placeholder"] = True
                        response_data["avatar_info"]["note"] = avatar_result.get("note", "使用占位符头像")
                    
                    logger.info(f"专属头像生成成功: {avatar_filename}")
                else:
                    # 头像生成失败
                    error_message = avatar_result.get("error", "未知错误")
                    response_data["avatar_info"] = {
                        "status": "error", 
                        "message": f"头像生成失败: {error_message}",
                        "error_details": avatar_result.get("debug_info", {})
                    }
                    logger.warning(f"头像生成失败: {error_message}")
                    
                    # 如果有备用头像路径，也提供给前端
                    if avatar_result.get("avatar_path"):
                        avatar_filename = os.path.basename(avatar_result["avatar_path"])
                        response_data["avatar_info"]["fallback_avatar_url"] = f"http://123.60.11.207/api/style/avatars/{avatar_filename}"
                        response_data["avatar_info"]["fallback_avatar_filename"] = avatar_filename
                
            except Exception as e:
                logger.error(f"头像生成过程出现异常: {str(e)}")
                response_data["avatar_info"] = {
                    "status": "error", 
                    "message": f"头像生成异常: {str(e)}",
                    "exception_type": type(e).__name__
                }
                
        elif request.generate_avatar and not user_image_paths:
            response_data["avatar_info"] = {
                "status": "no_user_images", 
                "message": "需要用户照片才能生成个性化头像"
            }
        
        # 更新最终进度状态
        final_message = "🎉 分析完成！为你量身定制的时尚建议已生成"
        if request.generate_avatar and response_data["avatar_info"]["status"] == "completed":
            final_message = "🎉 分析完成！专属建议和个性化头像都已为你准备好"
        elif request.generate_avatar and response_data["avatar_info"]["status"] == "error":
            final_message = "✅ 时尚分析完成，但头像生成遇到了问题"
        
        # 任务完成
        save_task_status(
            task_id, 
            TaskStatus.COMPLETED, 
            progress=final_message,
            result=response_data
        )
        
        logger.info(f"任务 {task_id} 完成处理，头像状态: {response_data['avatar_info']['status']}")
        
    except Exception as e:
        logger.error(f"处理任务 {task_id} 时发生错误: {str(e)}")
        
        # 生成通用错误回复
        fallback_result = {
            "success": False,
            "content": "系统处理过程中出现了意外错误，请稍后重试。如果问题持续存在，请联系客服支持。",
            "metadata": {
                "error_type": "system_error",
                "timestamp": datetime.now().isoformat(),
                "technical_error": str(e)
            },
            "avatar_info": {"status": "disabled", "message": "系统错误，无法生成头像"},
            "message": "系统处理错误"
        }
        
        save_task_status(
            task_id, 
            TaskStatus.COMPLETED,  # 使用COMPLETED而不是ERROR
            result=fallback_result,
            progress="❌ 系统处理过程中出现错误"
        )

@router.post("/analyze", response_model=TaskInitResponse)
async def analyze_style(request: StyleAnalysisRequest):
    """
    启动风格分析任务（异步处理）
    
    输入参数：
    - style_image_names: 喜欢的别人图片文件名列表（需先上传到对应目录）
    - user_image_names: 自己的图片文件名列表（需先上传到对应目录）
    - text_requirements: 用户文字需求描述
    - user_name: 用户昵称（可选，用于个性化回复）
    - page_session_id: 页面级session_id（有图片时必需，用于定位图片文件）
    
    要求：三个参数中至少有一个不能为空
    """
    try:
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        save_task_status(
            task_id, 
            TaskStatus.PENDING, 
            request_data=request.dict(),
            progress="任务已创建，等待处理..."
        )
        
        # 在后台启动异步处理任务
        asyncio.create_task(process_style_analysis_task(task_id, request))
        
        # 立即返回任务ID和状态
        return TaskInitResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="风格分析任务已启动，请使用task_id轮询状态",
            check_url=f"/api/style/task-status/{task_id}"
        )
        
    except Exception as e:
        logger.error(f"启动风格分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_api(task_id: str):
    """
    查询任务处理状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        TaskStatusResponse: 任务状态信息
    """
    try:
        task_info = get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        status = task_info["status"]
        
        if status == TaskStatus.COMPLETED:
            return TaskStatusResponse(
                success=True,
                task_id=task_id,
                status=status,
                progress=task_info.get("progress", "任务已完成"),
                result=task_info.get("result"),
                message="任务处理完成"
            )
        else:  # PENDING or RUNNING
            return TaskStatusResponse(
                success=True,
                task_id=task_id,
                status=status,
                progress=task_info.get("progress", "任务处理中..."),
                message="任务正在处理中"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-debug", response_model=TaskInitResponse)
async def analyze_style_debug(request: StyleAnalysisRequest):
    """
    启动风格分析任务（调试版本，返回详细数据）
    """
    try:
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态（调试模式）
        save_task_status(
            task_id, 
            TaskStatus.PENDING, 
            request_data=request.dict(),
            progress="调试任务已创建，等待处理...",
            debug_mode=True
        )
        
        # 在后台启动异步处理任务
        asyncio.create_task(process_style_analysis_task(task_id, request))
        
        # 立即返回任务ID和状态
        return TaskInitResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="风格分析任务已启动（调试模式），请使用task_id轮询状态",
            check_url=f"/api/style/task-status/{task_id}"
        )
        
    except Exception as e:
        logger.error(f"启动风格分析任务失败（调试模式）: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "style-analysis-v2"}

@router.get("/avatar-status/{page_session_id}")
async def get_avatar_status(page_session_id: str):
    """
    查询头像生成状态（兼容性接口，现在头像和主结果一起返回）
    
    Args:
        page_session_id: 页面级会话ID
        
    Returns:
        Dict: 头像状态和文件信息
    """
    try:
        avatar_generator = await get_avatar_generator()
        status_info = avatar_generator.get_avatar_status(page_session_id)
        
        if status_info["status"] == "completed":
            # 构建完整的文件URL（假设服务运行在本地8000端口）
            avatar_filename = status_info["avatar_filename"]
            avatar_url = f"http://123.60.11.207/api/style/avatars/{avatar_filename}"
            
            return {
                "success": True,
                "status": "completed",
                "avatar_url": avatar_url,
                "avatar_filename": avatar_filename,
                "file_size": status_info["file_size"],
                "generated_at": os.path.getctime(status_info["avatar_path"]),
                "message": "头像生成完成",
                "note": "此接口已弃用，头像现在和分析结果一起返回"
            }
        else:
            return {
                "success": True,
                "status": "not_found",
                "page_session_id": page_session_id,
                "message": "头像文件未找到，可能还在生成中或生成失败",
                "note": "此接口已弃用，头像现在和分析结果一起返回"
            }
            
    except Exception as e:
        logger.error(f"查询头像状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/avatars/{filename}")
async def get_avatar_file(filename: str):
    """
    获取生成的头像文件
    
    Args:
        filename: 头像文件名
        
    Returns:
        FileResponse: 头像图片文件
    """
    try:
        avatar_path = os.path.join("generated_avatars", filename)
        
        if not os.path.exists(avatar_path):
            raise HTTPException(status_code=404, detail="头像文件不存在")
        
        # 验证文件扩展名
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            raise HTTPException(status_code=400, detail="无效的文件格式")
            
        # 返回文件
        from fastapi.responses import FileResponse
        return FileResponse(avatar_path)
        
    except Exception as e:
        logger.error(f"获取头像文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 为了支持图片上传，添加文件上传接口
@router.post("/upload-images")
async def upload_images(
    files: List[UploadFile] = File(...),
    image_type: str = Form(...),  # "style" (喜欢的别人) 或 "user" (自己)
    page_session_id: Optional[str] = Form(None),  # 新增：页面级session_id
    prefixed_filename: Optional[str] = Form(None)  # 新增：带前缀的文件名
):
    """
    上传图片并保存到本地文件系统
    
    文件保存结构：
    user_data/
    └── {page_session_id}/
        ├── love/          # 喜欢的别人图片
        └── self/          # 自己的图片
    """
    if image_type not in ["style", "user"]:
        raise HTTPException(status_code=400, detail="image_type必须是 'style' 或 'user'")
    
    # 验证page_session_id
    if not page_session_id:
        raise HTTPException(status_code=400, detail="缺少页面session_id")
    
    # 确定保存目录
    subdir = "love" if image_type == "style" else "self"
    save_dir = os.path.join("user_data", page_session_id, subdir)
    
    # 确保目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    saved_files = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 不是图片格式")
        
        # 使用前端传来的带前缀文件名，如果没有则生成新的
        if prefixed_filename:
            # 从带前缀的文件名中提取页面session_id和原始文件名
            extracted_session_id, original_filename = extract_page_session_from_filename(prefixed_filename)
            
            if extracted_session_id and extracted_session_id != page_session_id:
                logger.warning(f"文件名中的session_id {extracted_session_id} 与参数不匹配 {page_session_id}")
            
            # 使用原始文件名保存
            save_filename = original_filename if original_filename else file.filename
        else:
            # 如果没有提供前缀文件名，生成唯一文件名
            file_extension = os.path.splitext(file.filename)[1]
            save_filename = f"{uuid.uuid4()}{file_extension}"
        
        file_path = os.path.join(save_dir, save_filename)
        
        # 保存文件
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            saved_files.append({
                "original_name": file.filename,
                "saved_name": save_filename,
                "path": file_path,
                "prefixed_name": prefixed_filename
            })
            
            logger.info(f"文件保存成功: {file_path}")
            
        except Exception as e:
            logger.error(f"保存文件失败 {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    
    return {
        "success": True,
        "page_session_id": page_session_id,
        "image_type": image_type,
        "saved_files": saved_files,
        "count": len(saved_files),
        "save_directory": save_dir,
        "tip": f"现在可以使用这些文件名调用 /analyze 接口：{[f['saved_name'] for f in saved_files]}"
    }

# 添加一个简单的测试接口
@router.post("/test-personalized-response")
async def test_personalized_response(test_data: dict):
    """
    测试个性化回复生成器（无需真实分析数据）
    """
    try:
        response_generator = await get_response_generator()
        
        # 创建一个模拟的分析结果用于测试
        from models.response_models import ComprehensiveAnalysisResult
        
        # 这里可以用测试数据
        mock_result = ComprehensiveAnalysisResult()
        mock_result.session_id = str(uuid.uuid4())
        
        personalized_response = await response_generator.generate_personalized_response(
            analysis_result=mock_result,
            user_name=test_data.get("user_name", "小仙女")
        )
        
        return {
            "success": True,
            "content": personalized_response["content"],
            "metadata": {
                "session_id": personalized_response["session_id"],
                "generated_at": personalized_response["generated_at"],
                "analysis_confidence": personalized_response.get("analysis_confidence", 0.7)
            },
            "message": "个性化回复测试成功"
        }
        
    except Exception as e:
        logger.error(f"测试个性化回复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 添加任务管理接口
@router.get("/tasks")
async def list_tasks():
    """获取所有任务列表（调试用）"""
    return {
        "success": True,
        "tasks": list(task_storage.values()),
        "count": len(task_storage)
    }

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除指定任务"""
    if task_id in task_storage:
        del task_storage[task_id]
        return {"success": True, "message": f"任务 {task_id} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="任务不存在")

@router.delete("/tasks")
async def clear_all_tasks():
    """清空所有任务（调试用）"""
    task_storage.clear()
    return {"success": True, "message": "所有任务已清空"}