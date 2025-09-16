from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
import json
import base64
import re
import aiohttp
from PIL import Image, ImageDraw, ImageFont

from models.database_models import User
from utils.auth import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/virtual-tryon", tags=["虚拟试穿"])

# 全局存储处理状态
processing_status = {}

class VirtualTryonService:
    """虚拟试穿服务 - 直接返回图片数据不是地址"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY', '')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "google/gemini-2.5-flash-image-preview"
        
        if not self.api_key:
            logger.warning("OpenRouter API密钥未配置")
    
    def combine_images_with_green_frame(self, user_image_path: str, clothes_image_paths: List[str]) -> str:
        """拼合图片，不使用绿框，用户图片更大，衣服图片更小"""
        try:
            user_img = Image.open(user_image_path)
            user_img = user_img.convert('RGB')
            
            # 增大用户图片尺寸
            user_width, user_height = 600, 900
            user_img = user_img.resize((user_width, user_height), Image.Resampling.LANCZOS)
            
            clothes_count = len(clothes_image_paths)
            # 缩小衣服图片尺寸
            clothes_width, clothes_height = 150, 150
            
            # 计算总的画布大小
            if clothes_count <= 3:
                total_width = user_width + clothes_width + 80
                total_height = max(user_height, clothes_height * clothes_count)
            else:
                cols = 2
                rows = (clothes_count + 1) // 2
                total_width = user_width + clothes_width * cols + 80
                total_height = max(user_height, clothes_height * rows)
            
            # 创建白色背景画布
            combined_img = Image.new('RGB', (total_width, total_height), (255, 255, 255))
            
            # 直接粘贴用户图片（不使用绿框）
            combined_img.paste(user_img, (20, 20))
            
            # 处理并粘贴衣服图片
            for i, clothes_path in enumerate(clothes_image_paths):
                try:
                    clothes_img = Image.open(clothes_path)
                    clothes_img = clothes_img.convert('RGB')
                    clothes_img = clothes_img.resize((clothes_width, clothes_height), Image.Resampling.LANCZOS)
                    
                    # 计算衣服图片位置
                    if clothes_count <= 3:
                        x = user_width + 40
                        y = 20 + i * (clothes_height + 20)
                    else:
                        col = i % 2
                        row = i // 2
                        x = user_width + 40 + col * (clothes_width + 20)
                        y = 20 + row * (clothes_height + 20)
                    
                    combined_img.paste(clothes_img, (x, y))
                    
                except Exception as e:
                    logger.warning(f"处理衣服图片失败: {clothes_path}, 错误: {str(e)}")
            
            combined_path = f"user_data/virtual_tryon/combined_{uuid.uuid4()}.jpg"
            os.makedirs(os.path.dirname(combined_path), exist_ok=True)
            combined_img.save(combined_path, 'JPEG', quality=95)
            
            logger.info(f"图片拼合成功: {combined_path}")
            return combined_path
            
        except Exception as e:
            logger.error(f"图片拼合失败: {str(e)}")
            raise
    
    async def generate_with_gemini(self, prompt: str, image_path: str, output_path: str) -> str:
        """使用Gemini生成虚拟试穿效果 - 按照1.py和2.py的方式"""
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 验证API密钥是否存在
            if not self.api_key:
                raise Exception("OpenRouter API密钥未配置")
            
            payload = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }],
                "modalities": ["image", "text"]
            }
            
            logger.info(f"准备调用Gemini API, payload大小: {len(str(payload))}字符")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    logger.info(f"Gemini API响应状态: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Gemini API请求失败详情: {error_text}")
                        raise Exception(f"Gemini API请求失败: {response.status}, {error_text}")
                    
                    result = await response.json()
                    logger.info(f"Gemini API返回结果结构: {list(result.keys())}")
                    
                    if "choices" not in result or not result["choices"]:
                        raise Exception("Gemini API返回格式错误: 缺少choices字段")
                    
                    message = result["choices"][0]["message"]
                    if "images" not in message or not message["images"]:
                        raise Exception("Gemini未返回图片: 缺少images字段")
                    
                    img_url = message["images"][0]["image_url"]["url"]
                    logger.info(f"成功获取图片URL, 长度: {len(img_url)}字符")

                    # 按照1.py的方式解码
                    b64_data = re.sub(r"^data:image/[^;]+;base64,", "", img_url)
                    
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    
                    logger.info(f"Gemini生成成功: {output_path}")
                    return output_path
                    
        except Exception as e:
            error_message = str(e)
            logger.error(f"Gemini生成失败: {error_message}")
            
            # 准备回退方案信息
            fallback_info = {
                "original_error": error_message,
                "fallback_used": False,
                "copy_success": False
            }
            
            # 当API调用失败时，复制原始图片作为结果
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 复制原始拼合图片作为结果
                import shutil
                shutil.copy2(image_path, output_path)
                fallback_info["copy_success"] = True
                fallback_info["fallback_used"] = True
                logger.warning(f"API调用失败，使用原始拼合图片作为结果: {output_path}")
                
                # 不抛出异常，而是返回回退信息，让调用方决定如何处理
                return output_path
            except Exception as copy_error:
                fallback_info["copy_error"] = str(copy_error)
                logger.error(f"复制原始图片也失败: {str(copy_error)}")
                
                # 复制失败，抛出包含完整回退信息的异常
                raise Exception(f"生成失败，回退机制也失败: 原始错误={error_message}, 复制错误={str(copy_error)}")
    
    def image_to_base64(self, image_path: str) -> str:
        """将图片文件转换为base64数据"""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_data}"
        except Exception as e:
            logger.error(f"图片转base64失败: {str(e)}")
            raise
    
    async def process_virtual_tryon(self, session_id: str, user_id: int, user_image_path: str, clothes_image_paths: List[str]):
        """处理虚拟试穿请求"""
        try:
            processing_status[session_id] = {
                "status": "processing",
                "user_id": user_id,
                "start_time": datetime.now(),
                "progress": 10
            }
            
            logger.info(f"开始处理虚拟试穿: session={session_id}, user={user_id}")
            
            # 拼合图片，用绿框标识用户
            combined_image_path = self.combine_images_with_green_frame(user_image_path, clothes_image_paths)
            
            processing_status[session_id]["progress"] = 30
            
            # 构建prompt - 不依赖绿框，而是通过位置和大小来区分
            prompt = """
            请基于提供的图片生成虚拟试穿效果。

            重要说明：
            - 左侧占据大部分画面的大图片是用户本人
            - 右侧的小图片是用户想要试穿的衣服
            - 请将右侧的衣服自然地穿在用户身上

            生成要求：
            1. 保持用户的面部特征、体型和姿势不变
            2. 将衣服的颜色、款式、材质真实地呈现在用户身上
            3. 确保服装与用户体型协调，穿着效果自然
            4. 保持合适的光影效果，使穿搭看起来真实
            5. 如果有多件衣服，请合理搭配穿着
            6. 背景可以适当美化，突出整体穿搭效果
            7. 请确保生成的图像质量高，细节清晰，没有模糊或扭曲
            8. 返回的照片中只能包含用户本人的虚拟试衣照片，不要有除了用户本人的虚拟试衣之外的其他图片夹杂在里面。

            请生成高质量、真实自然的虚拟试穿效果图。
            """
            
            processing_status[session_id]["progress"] = 50
            
            # 使用Gemini生成试穿效果
            result_image_path = f"user_data/virtual_tryon/result_{session_id}_{uuid.uuid4()}.jpg"
            
            try:
                # 尝试调用Gemini API生成图片
                final_image_path = await self.generate_with_gemini(prompt, combined_image_path, result_image_path)
                
                # 检查结果是否为回退的原始图片
                # 由于generate_with_gemini现在在回退成功时返回路径而不是抛出异常，我们需要通过文件名判断
                # 如果是原始图片副本，文件名应该是result_开头
                is_fallback_to_original = False
                
                # 检查结果是否是原始图片副本（通过比较文件大小）
                if os.path.exists(final_image_path) and os.path.exists(combined_image_path):
                    original_size = os.path.getsize(combined_image_path)
                    result_size = os.path.getsize(final_image_path)
                    # 如果大小相近，可能是原始图片的副本
                    is_fallback_to_original = abs(original_size - result_size) < 1024  # 允许1KB的差异
                
                # 无论是否回退，都转换为base64数据
                result_image_data = self.image_to_base64(final_image_path)
                
                # 根据是否回退设置不同的状态和置信度
                if is_fallback_to_original:
                    # 回退方案被使用
                    processing_status[session_id] = {
                        "status": "partial_completed",
                        "user_id": user_id,
                        "result_image_data": result_image_data,
                        "fallback_used": True,
                        "confidence": 50,
                        "processing_time": (datetime.now() - processing_status[session_id]["start_time"]).total_seconds(),
                        "completed_time": datetime.now()
                    }
                    logger.warning(f"虚拟试穿处理完成但使用了回退方案: {session_id}")
                else:
                    # 正常完成
                    processing_status[session_id]["progress"] = 90
                    processing_status[session_id] = {
                        "status": "completed",
                        "user_id": user_id,
                        "result_image_data": result_image_data,
                        "fallback_used": False,
                        "confidence": 95,
                        "processing_time": (datetime.now() - processing_status[session_id]["start_time"]).total_seconds(),
                        "completed_time": datetime.now()
                    }
                    logger.info(f"虚拟试穿处理完成: {session_id}")
                
            except Exception as api_error:
                # API调用失败且回退机制也失败时的处理
                logger.error(f"Gemini API调用失败且回退机制也失败: {str(api_error)}")
                
                # 无论如何，尝试获取结果图片（可能是原始图片的副本）
                if os.path.exists(result_image_path):
                    result_image_data = self.image_to_base64(result_image_path)
                elif os.path.exists(combined_image_path):
                    # 如果没有结果图片，使用拼合图片
                    result_image_data = self.image_to_base64(combined_image_path)
                else:
                    result_image_data = None
                
                # 更新状态为失败
                processing_status[session_id] = {
                    "status": "failed",
                    "user_id": user_id,
                    "result_image_data": result_image_data,
                    "error": str(api_error),
                    "confidence": 0,
                    "processing_time": (datetime.now() - processing_status[session_id]["start_time"]).total_seconds(),
                    "completed_time": datetime.now()
                }
                
                logger.error(f"虚拟试穿处理失败: {session_id}, 原因: {str(api_error)}")
            
        except Exception as e:
            logger.error(f"虚拟试穿处理过程失败: {session_id}, 错误: {str(e)}")
            
            # 尝试使用拼合图片作为最后的回退
            try:
                result_image_data = self.image_to_base64(combined_image_path)
                fallback_used = True
            except Exception:
                result_image_data = None
                fallback_used = False
            
            processing_status[session_id] = {
                "status": "failed",
                "user_id": user_id,
                "result_image_data": result_image_data if fallback_used else None,
                "error": str(e),
                "fallback_used": fallback_used,
                "failed_time": datetime.now()
            }

tryon_service = VirtualTryonService()

@router.post("/upload-user-image")
async def upload_user_image(
    user_id: str = Form(...),
    session_id: str = Form(...),
    image_type: str = Form(...),
    user_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token)
):
    """上传用户图片文件"""
    try:
        if int(user_id) != current_user.id:
            raise HTTPException(status_code=403, detail="用户ID不匹配")
        
        if image_type != 'user':
            raise HTTPException(status_code=400, detail="图片类型错误")
        
        session_dir = f"user_data/virtual_tryon/user_{current_user.id}/{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        user_image_path = f"{session_dir}/user_image.jpg"
        with open(user_image_path, "wb") as f:
            content = await user_image.read()
            f.write(content)
        
        logger.info(f"用户图片上传成功: {user_image_path}")
        
        return {
            "success": True,
            "message": "用户图片上传成功",
            "image_path": user_image_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户图片上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传失败")

@router.post("/upload-clothes-image")
async def upload_clothes_image(
    user_id: str = Form(...),
    session_id: str = Form(...),
    image_type: str = Form(...),
    clothes_index: str = Form(...),
    clothes_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token)
):
    """上传衣服图片文件"""
    try:
        if int(user_id) != current_user.id:
            raise HTTPException(status_code=403, detail="用户ID不匹配")
        
        if image_type != 'clothes':
            raise HTTPException(status_code=400, detail="图片类型错误")
        
        session_dir = f"user_data/virtual_tryon/user_{current_user.id}/{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        clothes_image_path = f"{session_dir}/clothes_{clothes_index}.jpg"
        with open(clothes_image_path, "wb") as f:
            content = await clothes_image.read()
            f.write(content)
        
        logger.info(f"衣服图片上传成功: {clothes_image_path}")
        
        return {
            "success": True,
            "message": f"衣服图片{clothes_index}上传成功",
            "image_path": clothes_image_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"衣服图片上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传失败")

@router.post("/start-processing")
async def start_processing(
    request: dict,
    current_user: User = Depends(get_current_user_from_token)
):
    """开始处理虚拟试穿"""
    try:
        user_id = request.get('user_id')
        session_id = request.get('session_id')
        clothes_count = request.get('clothes_count')
        
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="用户ID不匹配")
        
        session_dir = f"user_data/virtual_tryon/user_{current_user.id}/{session_id}"
        user_image_path = f"{session_dir}/user_image.jpg"
        
        if not os.path.exists(user_image_path):
            raise HTTPException(status_code=400, detail="用户图片未上传")
        
        clothes_image_paths = []
        for i in range(clothes_count):
            clothes_path = f"{session_dir}/clothes_{i}.jpg"
            if os.path.exists(clothes_path):
                clothes_image_paths.append(clothes_path)
        
        if len(clothes_image_paths) == 0:
            raise HTTPException(status_code=400, detail="衣服图片未上传")
        
        # 异步开始处理
        asyncio.create_task(tryon_service.process_virtual_tryon(
            session_id, current_user.id, user_image_path, clothes_image_paths
        ))
        
        logger.info(f"开始处理虚拟试穿: 用户{current_user.id}, 会话{session_id}")
        
        return {
            "success": True,
            "message": "开始处理虚拟试穿",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="处理失败")

@router.get("/result/{session_id}")
async def get_tryon_result(
    session_id: str,
    current_user: User = Depends(get_current_user_from_token)
):
    """获取虚拟试穿结果 - 返回图片数据不是地址"""
    try:
        if session_id not in processing_status:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        status_info = processing_status[session_id]
        
        if status_info.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此会话")
        
        if "start_time" in status_info:
            if datetime.now() - status_info["start_time"] > timedelta(minutes=5):
                del processing_status[session_id]
                raise HTTPException(status_code=408, detail="处理超时")
        
        return {
            "session_id": session_id,
            **status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取处理结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取结果失败")

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "virtual-tryon",
        "active_sessions": len(processing_status),
        "implementation": "direct_image_data_not_url"
    }