import asyncio
import logging
import json
import os
import uuid
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime
from doubao_client import DoubaoClient, ChatMessage, MessageRole, MessageContent, MessageContentType
from models.response_models import ComprehensiveAnalysisResult

logger = logging.getLogger(__name__)

class AvatarGenerator:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seedream-3-0-t2i-250415"):
        self.client = doubao_client
        self.model_name = model_name
        self.avatar_save_dir = "generated_avatars"
        
        # 确保保存目录存在
        os.makedirs(self.avatar_save_dir, exist_ok=True)
        
        # 验证模型名称是否适合图像生成
        if "seedream" not in model_name.lower() and "seededit" not in model_name.lower():
            logger.warning(f"模型 {model_name} 可能不是图像生成模型，建议使用seedream或seededit系列")
    
    async def generate_styled_avatar(
        self,
        analysis_result: ComprehensiveAnalysisResult,
        user_image_paths: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于用户分析结果生成个性化卡通头像
        
        Args:
            analysis_result: 综合分析结果
            user_image_paths: 用户照片路径列表
            session_id: 会话ID（现在通常是avatar_task_id）
            
        Returns:
            Dict: 生成结果信息
        """
        try:
            session_id = session_id or str(uuid.uuid4())
            logger.info(f"开始为会话 {session_id} 生成个性化卡通头像")
            
            # 构建头像生成的prompt
            avatar_prompt = self._build_avatar_generation_prompt(analysis_result)
            
            # 准备消息内容
            content_list = [
                MessageContent(type=MessageContentType.TEXT, text=avatar_prompt)
            ]
            
            # 如果有用户照片，添加到消息中作为参考
            if user_image_paths:
                for image_path in user_image_paths:
                    if os.path.exists(image_path):
                        # 读取并转换图片
                        with open(image_path, "rb") as f:
                            image_data = f.read()
                        
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        
                        # 检测图片类型
                        import mimetypes
                        mime_type, _ = mimetypes.guess_type(image_path)
                        mime_type = mime_type or "image/jpeg"
                        
                        content_list.append(
                            MessageContent(
                                type=MessageContentType.IMAGE_URL,
                                image_url={
                                    "url": f"data:{mime_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            )
                        )
            
            # 构建消息
            messages = [
                ChatMessage(
                    role=MessageRole.USER,
                    content=content_list
                )
            ]
            print(avatar_prompt)
            # 调用图像生成API - 使用正确的图像生成端点
            avatar_info = await self._call_image_generation_api(
                messages=messages,
                session_id=session_id,
                prompt=avatar_prompt
            )
            
            logger.info(f"卡通头像生成完成，会话ID: {session_id}")
            return avatar_info
            
        except Exception as e:
            logger.error(f"生成卡通头像失败: {str(e)}")
            # 尝试创建占位符头像作为备用
            placeholder_path = self._create_placeholder_avatar(session_id)
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "avatar_path": placeholder_path,
                "is_placeholder": True,
                "note": "头像生成失败，使用占位符"
            }
    
    async def _call_image_generation_api(self, messages: List[ChatMessage], session_id: str, prompt: str) -> Dict[str, Any]:
        """
        调用豆包图像生成API - 使用正确的图像生成端点
        
        Args:
            messages: 消息列表（包含prompt和图片参考）
            session_id: 会话ID（avatar_task_id）
            prompt: 完整的头像生成prompt
            
        Returns:
            Dict: 包含生成的头像信息
        """
        try:
            logger.info(f"使用图像生成模型: {self.model_name}")
            
            # 直接使用专门的图像生成API
            response_data = await self.client.create_image_generation(
                model=self.model_name,
                prompt=prompt,
                size="1024x1024",
                n=1,
                quality="high",
                style="vivid",
                response_format="b64_json"  # 获取base64编码的图片
            )
            
            # 处理图像生成响应
            if response_data and "data" in response_data:
                image_data = response_data["data"][0]
                
                # 处理base64图片数据
                if "b64_json" in image_data:
                    base64_data = image_data["b64_json"]
                    avatar_info = await self._process_base64_image(base64_data, session_id)
                    return avatar_info
                elif "url" in image_data:
                    # 处理图片URL
                    image_url = image_data["url"]
                    avatar_info = await self._process_image_url(image_url, session_id)
                    return avatar_info
                else:
                    raise ValueError("API响应格式不正确")
            
            elif response_data.get("note") == "使用备选方案":
                # 备选方案响应
                logger.warning("使用备选方案，创建占位符头像")
                avatar_path = self._create_placeholder_avatar(session_id)
                return {
                    "success": True,
                    "avatar_path": avatar_path,
                    "avatar_url": f"/api/style/avatars/avatar_{session_id}.png",
                    "session_id": session_id,
                    "generated_at": datetime.now().isoformat(),
                    "model": self.model_name,
                    "is_placeholder": True,
                    "note": "当前使用占位符，需要检查豆包API配置"
                }
            
            else:
                raise ValueError("无效的API响应格式")
                
        except Exception as e:
            logger.error(f"图像生成API调用失败: {str(e)}")
            
            # 创建占位符作为备选
            avatar_path = self._create_placeholder_avatar(session_id)
            
            return {
                "success": False,
                "error": str(e),
                "model": self.model_name,
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "avatar_path": avatar_path,
                "avatar_url": f"/api/style/avatars/avatar_{session_id}.png",
                "is_placeholder": True,
                "debug_info": {
                    "prompt_length": len(prompt),
                    "api_endpoint": "images/generations"
                }
            }
    
    async def _process_base64_image(self, base64_data: str, session_id: str) -> Dict[str, Any]:
        """处理base64编码的图片数据"""
        try:
            # 解码base64数据
            image_data = base64.b64decode(base64_data)
            
            # 保存图片文件 - 使用avatar_task_id命名
            avatar_filename = f"avatar_{session_id}.png"
            avatar_path = os.path.join(self.avatar_save_dir, avatar_filename)
            
            with open(avatar_path, "wb") as f:
                f.write(image_data)
            
            logger.info(f"头像保存成功: {avatar_path}")
            
            return {
                "success": True,
                "avatar_path": avatar_path,
                "avatar_url": f"/api/style/avatars/{avatar_filename}",
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "model": self.model_name,
                "file_size": len(image_data),
                "format": "PNG"
            }
            
        except Exception as e:
            logger.error(f"处理base64图片失败: {str(e)}")
            raise
    
    async def _process_image_url(self, image_url: str, session_id: str) -> Dict[str, Any]:
        """处理图片URL"""
        try:
            # 下载图片
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # 保存图片文件 - 使用avatar_task_id命名
            avatar_filename = f"avatar_{session_id}.png"
            avatar_path = os.path.join(self.avatar_save_dir, avatar_filename)
            
            with open(avatar_path, "wb") as f:
                f.write(image_data)
            
            logger.info(f"头像下载并保存成功: {avatar_path}")
            
            return {
                "success": True,
                "avatar_path": avatar_path,
                "avatar_url": f"/api/style/avatars/{avatar_filename}",
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "model": self.model_name,
                "source_url": image_url,
                "file_size": len(image_data)
            }
            
        except Exception as e:
            logger.error(f"处理图片URL失败: {str(e)}")
            raise
    
    def _create_placeholder_avatar(self, session_id: str) -> str:
        """创建占位符头像（用于测试和开发）"""
        try:
            # 创建一个简单的占位符图片
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # 创建1024x1024的图像
            img = Image.new('RGB', (1024, 1024), color='#f0f0f0')
            draw = ImageDraw.Draw(img)
            
            # 绘制占位符文本
            text = f"Avatar\n{session_id[:12]}"
            try:
                font = ImageFont.truetype("arial.ttf", 48)
            except:
                font = ImageFont.load_default()
            
            # 计算文本位置
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (1024 - text_width) // 2
            y = (1024 - text_height) // 2
            
            draw.text((x, y), text, fill='#666666', font=font)
            
            # 绘制简单的边框
            draw.rectangle([50, 50, 974, 974], outline='#cccccc', width=5)
            
            # 保存图片 - 使用avatar_task_id命名
            avatar_path = os.path.join(self.avatar_save_dir, f"avatar_{session_id}.png")
            img.save(avatar_path)
            
            logger.info(f"占位符头像创建成功: {avatar_path}")
            return avatar_path
            
        except Exception as e:
            logger.error(f"创建占位符头像失败: {str(e)}")
            return None

    def _build_avatar_generation_prompt(self, analysis_result: ComprehensiveAnalysisResult) -> str:
        """构建头像生成的prompt"""
        
        # 验证分析结果的完整性
        if not analysis_result:
            raise ValueError("分析结果不能为空")
        
        # 提取用户特征信息
        user_features = ""
        if analysis_result.user_analysis:
            user = analysis_result.user_analysis
            user_features = f"""
## 用户外观特征：
- 肤色类型：{user.skin_tone.tone_type}（适合颜色：{', '.join(user.skin_tone.suitable_colors[:3])}）
- 脸型：{user.face_shape.shape}（适合领型：{', '.join(user.face_shape.suitable_necklines[:2])}）
- 整体体型：{user.body_type.overall}
- 身材比例：{user.body_type.proportions}
- 适合版型：{', '.join(user.body_type.best_silhouettes[:2])}
- 个人气质：{user.personal_style.temperament}
- 推荐个人风格：{', '.join(user.personal_style.recommended_styles[:2])}
"""
        else:
            user_features = "\n## 用户外观特征：用户照片分析数据缺失，请根据参考照片推测特征\n"
        
        # 提取推荐穿搭信息
        outfit_suggestions = ""
        if analysis_result.final_recommendation and analysis_result.final_recommendation.outfit_recommendations:
            outfits = analysis_result.final_recommendation.outfit_recommendations
            # 选择第一个推荐方案作为生成基础
            if outfits:
                main_outfit = outfits[0]
                outfit_suggestions = f"""
## 推荐穿搭方案（{main_outfit.theme}）：
"""
                for item in main_outfit.items:
                    outfit_suggestions += f"- {item.category}：{item.description}，颜色：{item.color}，选择理由：{item.why_suitable}\n"
                
                outfit_suggestions += f"\n整体效果预期：{main_outfit.overall_effect}\n"
                
                # 如果有多个方案，也提及备选方案的特色
                if len(outfits) > 1:
                    outfit_suggestions += f"\n备选风格参考：{outfits[1].theme if len(outfits) > 1 else ''}\n"
        else:
            outfit_suggestions = "\n## 推荐穿搭方案：最终推荐方案缺失，请基于风格偏好设计合适的穿搭\n"
        
        # 提取风格信息
        style_info = ""
        if analysis_result.style_analysis:
            style = analysis_result.style_analysis
            style_info = f"""
## 用户喜爱的风格：
- 整体风格：{style.overall_style}
- 风格关键词：{', '.join(style.style_keywords)}
- 主要色调：{', '.join(style.color_scheme.primary_colors)}
- 色彩情绪：{style.color_scheme.color_mood}
- 适合场合：{', '.join(style.occasions)}
- 风格描述：{style.style_description}
"""
        else:
            style_info = "\n## 用户喜爱的风格：用户风格偏好数据缺失，请设计清新自然的风格\n"
        
        # 提取文字需求信息
        context_info = ""
        if analysis_result.text_analysis:
            text = analysis_result.text_analysis
            context_info = f"""
## 使用场景：
- 目标场合：{text.occasion or '日常生活'}
- 特殊要求：{', '.join(text.special_requirements) if text.special_requirements else '无特殊要求'}
- 优先需求：{text.priority or '整体协调美观'}
"""
        
        prompt = f"""
请生成一个高质量的iOS风格3D贴纸卡通头像，严格按照以下要求执行：

{user_features}
{style_info}
{outfit_suggestions}
{context_info}

## 📱 iOS风格要求：
1. **视觉风格**：
   - 模仿苹果iOS系统Memoji/Animoji的官方3D贴纸风格
   - 可爱、友好、现代的卡通风格，带有苹果的设计美学
   - 高质量3D渲染效果，有立体感、柔和光影和细腻质感
   - 色彩饱和度适中，符合iOS系统的视觉规范

2. **人物特征还原**：
   - 严格根据用户肤色类型设计角色肤色
   - 根据脸型特征精确设计五官比例和头部形状
   - 体现分析出的个人气质和特点
   - 表情自然友好，带有自信的微笑

3. **服装搭配实现**：
   - **必须严格按照推荐的穿搭方案设计服装**
   - 颜色搭配完全与分析建议一致
   - 服装风格精确体现用户的时尚偏好
   - 注意每个细节：上衣、下装、鞋子、配饰等都要符合建议
   - 面料质感要通过3D渲染体现出来

4. **技术规格**：
   - 背景：纯白色或透明背景
   - 构图：人物居中，3/4身像或全身像
   - 分辨率：高清质量，适合移动端和桌面端展示
   - 整体风格统一，看起来像苹果官方制作的贴纸

5. **姿势和表情**：
   - 自然自信的姿势，可以有轻微的时尚pose
   - 表情阳光友好，体现穿搭后的美好自信状态
   - 肢体语言要符合整体风格的气质

## 🎯 特别注意：
- 如果某些分析数据缺失，请根据可用信息做出合理推测
- 确保最终形象既有个人特色又符合iOS美学标准
- 重点突出推荐穿搭的视觉效果，让用户能直观看到建议的搭配效果

请生成一个完美符合以上所有要求的3D卡通头像。
"""
        
        return prompt
    
    async def _process_avatar_response(self, response_text: str, session_id: str) -> Dict[str, Any]:
        """处理头像生成响应"""
        try:
            # 这里的处理逻辑需要根据实际API响应格式调整
            # 假设响应包含图片的base64编码或URL
            
            # 生成唯一文件名 - 使用avatar_task_id
            avatar_filename = f"avatar_{session_id}.png"
            avatar_path = os.path.join(self.avatar_save_dir, avatar_filename)
            
            # 如果响应是base64编码的图片
            if "base64" in response_text.lower() or response_text.startswith("data:image"):
                # 提取base64数据
                if "base64," in response_text:
                    base64_data = response_text.split("base64,")[1]
                else:
                    base64_data = response_text
                
                # 解码并保存图片
                image_data = base64.b64decode(base64_data)
                with open(avatar_path, "wb") as f:
                    f.write(image_data)
                
                return {
                    "success": True,
                    "avatar_filename": avatar_filename,
                    "avatar_path": avatar_path,
                    "session_id": session_id,
                    "generated_at": datetime.now().isoformat(),
                    "file_size": len(image_data)
                }
            
            # 如果响应是图片URL
            elif response_text.startswith("http"):
                # 下载图片并保存到本地
                import httpx
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(response_text)
                    if img_response.status_code == 200:
                        with open(avatar_path, "wb") as f:
                            f.write(img_response.content)
                        
                        return {
                            "success": True,
                            "avatar_filename": avatar_filename,
                            "avatar_path": avatar_path,
                            "session_id": session_id,
                            "generated_at": datetime.now().isoformat(),
                            "original_url": response_text,
                            "file_size": len(img_response.content)
                        }
            
            # 如果响应格式不符合预期
            else:
                logger.warning(f"未识别的图片响应格式: {response_text[:100]}...")
                return {
                    "success": False,
                    "error": "未能识别的图片响应格式",
                    "response_preview": response_text[:200],
                    "session_id": session_id,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"处理头像响应失败: {str(e)}")
            return {
                "success": False,
                "error": f"处理头像响应失败: {str(e)}",
                "session_id": session_id,
                "generated_at": datetime.now().isoformat()
            }
    
    def get_avatar_status(self, session_id: str) -> Dict[str, Any]:
        """获取头像生成状态"""
        avatar_pattern = f"avatar_{session_id}"
        
        # 检查是否存在该session的头像文件
        for filename in os.listdir(self.avatar_save_dir):
            if filename.startswith(avatar_pattern):
                avatar_path = os.path.join(self.avatar_save_dir, filename)
                return {
                    "status": "completed",
                    "avatar_filename": filename,
                    "avatar_path": avatar_path,
                    "file_exists": True,
                    "file_size": os.path.getsize(avatar_path)
                }
        
        return {
            "status": "not_found",
            "session_id": session_id,
            "message": "头像文件未找到，可能还在生成中或生成失败"
        }


# 使用示例
async def example_usage():
    """使用示例"""
    async with DoubaoClient() as client:
        generator = AvatarGenerator(client)
        
        print("个性化卡通头像生成器已准备就绪！")
        
        # 示例：生成头像
        # result = await generator.generate_styled_avatar(
        #     analysis_result=some_analysis_result,
        #     user_image_paths=["path/to/user/photo.jpg"],
        #     session_id="avatar_task_123_page_456"
        # )

if __name__ == "__main__":
    asyncio.run(example_usage())