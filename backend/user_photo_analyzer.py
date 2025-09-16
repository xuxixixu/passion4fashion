import json
import asyncio
import logging
import os
import base64
import mimetypes
from typing import List, Optional
from doubao_client import DoubaoClient, ChatMessage, MessageRole, MessageContent, MessageContentType
from models.response_models import UserAnalysisResult
from prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)

class UserPhotoAnalyzer:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seed-1-6-250615"):
        self.client = doubao_client
        self.model_name = model_name
        self.prompt_template = PromptTemplates()
    
    async def analyze_user_photos(
        self, 
        image_paths: List[str],
        detail_level: str = "high"  # 用户照片建议用高精度分析
    ) -> UserAnalysisResult:
        """
        分析一张或多张用户照片，提取个人特征
        
        Args:
            image_paths: 用户照片本地文件路径列表
            detail_level: 图片分析详细程度 ("low", "high", "auto")
            
        Returns:
            UserAnalysisResult: 用户分析结果
        """
        try:
            if not image_paths:
                raise ValueError("至少需要提供一张用户照片")
            
            logger.info(f"开始分析 {len(image_paths)} 张用户照片")
            
            # 验证文件存在
            for path in image_paths:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"图片文件不存在: {path}")
            
            # 第一步：验证图片内容是否适合用户分析
            validation_result = await self._validate_user_photos(image_paths, detail_level)
            if not validation_result["is_valid"]:
                # 如果图片不合适，抛出具体的错误
                raise ValueError(f"图片内容不适合用户分析: {validation_result['reason']}")
            
            # 第二步：进行具体的用户分析
            return await self._perform_user_analysis(image_paths, detail_level)
            
        except Exception as e:
            logger.error(f"用户照片分析失败: {str(e)}")
            raise

    async def _validate_user_photos(self, image_paths: List[str], detail_level: str) -> dict:
        """
        验证图片是否包含适合用户分析的内容
        
        Returns:
            dict: {"is_valid": bool, "reason": str, "content_type": str}
        """
        try:
            logger.info("正在验证图片内容是否适合用户分析...")
            
            # 构建验证消息内容
            content_list = []
            
            # 添加验证prompt
            validation_prompt = self._get_user_validation_prompt(len(image_paths))
            content_list.append(MessageContent(type=MessageContentType.TEXT, text=validation_prompt))
            
            # 添加所有图片
            for i, image_path in enumerate(image_paths):
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(image_path)
                mime_type = mime_type or "image/jpeg"
                
                content_list.append(
                    MessageContent(
                        type=MessageContentType.IMAGE_URL,
                        image_url={
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": detail_level
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
            
            # 调用API进行验证
            response = await self.client.create_chat_completion(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # 很低的随机性，确保验证结果稳定
                max_tokens=512
            )
            
            # 解析验证响应
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"用户图片验证API响应: {response_text}")
            
            # 清理markdown格式
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # 解析JSON
            try:
                validation_result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"用户验证结果JSON解析失败: {e}, 响应内容: {response_text}")
                # 如果解析失败，默认允许通过，避免误杀
                return {
                    "is_valid": True,
                    "reason": "验证服务异常，默认通过",
                    "content_type": "unknown",
                    "confidence": 0.5
                }
            
            logger.info(f"用户图片验证结果: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"用户图片内容验证失败: {str(e)}")
            # 验证失败时默认通过，避免影响正常功能
            return {
                "is_valid": True,
                "reason": f"验证过程异常: {str(e)}",
                "content_type": "unknown",
                "confidence": 0.5
            }
    
    def _get_user_validation_prompt(self, image_count: int) -> str:
        """获取用户照片验证的prompt"""
        image_instruction = f"这{image_count}张图片" if image_count > 1 else "这张图片"
        
        return f"""
你是一位专业的图片内容识别专家。请判断{image_instruction}是否适合进行用户个人特征分析（如体型、肤色、脸型分析）。

请仔细观察{image_instruction}，判断是否包含以下用户分析所需的内容：
✅ 合适的内容包括：
- 清晰的人物照片（能看到面部）
- 全身照或半身照
- 自拍照片
- 生活照片（包含人物主体）
- 能看到人物体型和外貌特征的照片
- 正常的人像摄影作品

❌ 不合适的内容包括：
- 纯风景照片
- 食物图片
- 动物图片
- 建筑物图片
- 抽象艺术图片
- 文字截图
- 无人物的图片
- 人物过于模糊或距离太远的图片
- 卡通人物或虚拟形象
- 明显非真人的图片

评判标准：
1. 图片中是否有清晰可见的真实人物
2. 是否能够分析出人物的外貌特征（肤色、体型、脸型等）
3. 图片质量是否足以进行个人特征分析
4. 人物是否为图片的主要内容

请用以下JSON格式返回判断结果，不要包含任何其他文字：
{{
  "is_valid": true/false,
  "reason": "详细说明判断原因",
  "content_type": "人物照片/风景照片/食物图片/动物图片/其他",
  "confidence": 0.95,
  "has_person": true/false,
  "person_visibility": "清晰可见/模糊不清/距离太远/无人物",
  "suitable_for_analysis": "说明是否适合个人特征分析及原因"
}}

如果图片不包含清晰可见的真实人物，或无法进行有效的个人特征分析，请将is_valid设置为false。
"""
    
    async def _perform_user_analysis(self, image_paths: List[str], detail_level: str) -> UserAnalysisResult:
        """执行具体的用户分析"""
        logger.info("开始执行具体的用户特征分析...")
        
        # 构建消息内容
        content_list = []
        
        # 添加原有的用户分析prompt
        prompt = self.prompt_template.get_user_analysis_prompt(len(image_paths))
        content_list.append(MessageContent(type=MessageContentType.TEXT, text=prompt))
        
        # 添加所有用户照片
        for i, image_path in enumerate(image_paths):
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            mime_type, _ = mimetypes.guess_type(image_path)
            mime_type = mime_type or "image/jpeg"
            
            content_list.append(
                MessageContent(
                    type=MessageContentType.IMAGE_URL,
                    image_url={
                        "url": f"data:{mime_type};base64,{image_base64}",
                        "detail": detail_level
                    }
                )
            )
            logger.debug(f"添加第 {i+1} 张用户照片: {image_path}")
        
        # 构建消息
        messages = [
            ChatMessage(
                role=MessageRole.USER,
                content=content_list
            )
        ]
        
        # 调用API
        response = await self.client.create_chat_completion(
            model=self.model_name,
            messages=messages,
            temperature=0.2,  # 更低的随机性，确保分析一致性
            max_tokens=2048
        )
        
        # 解析响应
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"用户分析API响应: {response_text}")
        
        # 清理可能的markdown格式
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # 解析JSON
        try:
            result_dict = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应内容: {response_text}")
            raise ValueError(f"AI返回的响应格式不正确: {e}")
        
        # 处理AI返回数据中可能的格式问题
        result_dict = self._normalize_user_analysis_result(result_dict)
        
        # 转换为结构化对象
        try:
            result = UserAnalysisResult(**result_dict)
        except Exception as e:
            logger.error(f"用户分析数据模型验证失败: {e}, 数据内容: {result_dict}")
            raise ValueError(f"AI返回的用户分析数据格式不符合预期: {e}")
        
        result.confidence_score = self._calculate_confidence_score(result, len(image_paths))
        logger.info(f"用户照片分析完成，肤色: {result.skin_tone.tone_type}, 体型: {result.body_type.overall}")
        print(result)
        return result
    
    async def analyze_single_user_photo(self, image_path: str) -> UserAnalysisResult:
        """
        分析单张用户照片的便捷方法
        
        Args:
            image_path: 单张用户照片本地文件路径
            
        Returns:
            UserAnalysisResult: 用户分析结果
        """
        return await self.analyze_user_photos([image_path])
    
    def _calculate_confidence_score(self, result: UserAnalysisResult, image_count: int) -> float:
        """
        计算分析结果的置信度
        """
        score = 0.6  # 基础分数
        
        # 多张照片可以提高置信度
        if image_count > 1:
            score += min(0.1 * (image_count - 1), 0.2)  # 最多额外增加0.2
        
        # 检查肤色分析的完整性
        if result.skin_tone.tone_type and result.skin_tone.suitable_colors:
            score += 0.15
        
        # 检查体型分析的完整性
        if result.body_type.overall and result.body_type.best_silhouettes:
            score += 0.15
        
        # 检查风格推荐的完整性
        if result.personal_style.recommended_styles and len(result.personal_style.recommended_styles) >= 2:
            score += 0.1
        
        # 检查脸型分析的完整性
        if result.face_shape.shape and result.face_shape.suitable_necklines:
            score += 0.05
        
        return min(score, 1.0)
    
    def _normalize_user_analysis_result(self, result_dict: dict) -> dict:
        """
        标准化AI返回的用户分析结果，处理可能的格式问题
        """
        try:
            # 处理body_type中的best_silhouettes字段：确保是列表
            if "body_type" in result_dict and "best_silhouettes" in result_dict["body_type"]:
                if isinstance(result_dict["body_type"]["best_silhouettes"], str):
                    result_dict["body_type"]["best_silhouettes"] = [result_dict["body_type"]["best_silhouettes"]]
                    logger.debug("转换best_silhouettes字段从字符串到列表")
            
            # 处理skin_tone中的suitable_colors字段：确保是列表
            if "skin_tone" in result_dict and "suitable_colors" in result_dict["skin_tone"]:
                if isinstance(result_dict["skin_tone"]["suitable_colors"], str):
                    result_dict["skin_tone"]["suitable_colors"] = [result_dict["skin_tone"]["suitable_colors"]]
                    logger.debug("转换suitable_colors字段从字符串到列表")
            
            # 处理skin_tone中的avoid_colors字段：确保是列表
            if "skin_tone" in result_dict and "avoid_colors" in result_dict["skin_tone"]:
                if isinstance(result_dict["skin_tone"]["avoid_colors"], str):
                    result_dict["skin_tone"]["avoid_colors"] = [result_dict["skin_tone"]["avoid_colors"]]
                    logger.debug("转换avoid_colors字段从字符串到列表")
            
            # 处理face_shape中的suitable_necklines字段：确保是列表
            if "face_shape" in result_dict and "suitable_necklines" in result_dict["face_shape"]:
                if isinstance(result_dict["face_shape"]["suitable_necklines"], str):
                    result_dict["face_shape"]["suitable_necklines"] = [result_dict["face_shape"]["suitable_necklines"]]
                    logger.debug("转换suitable_necklines字段从字符串到列表")
            
            # 处理personal_style中的recommended_styles字段：确保是列表
            if "personal_style" in result_dict and "recommended_styles" in result_dict["personal_style"]:
                if isinstance(result_dict["personal_style"]["recommended_styles"], str):
                    result_dict["personal_style"]["recommended_styles"] = [result_dict["personal_style"]["recommended_styles"]]
                    logger.debug("转换recommended_styles字段从字符串到列表")
            
            return result_dict
            
        except Exception as e:
            logger.warning(f"标准化用户分析结果时出现问题: {e}, 返回原始数据")
            return result_dict


# 使用示例
async def example_usage():
    async with DoubaoClient() as client:
        analyzer = UserPhotoAnalyzer(client)
        
        print("用户照片分析器已就绪！现在会先验证图片内容是否包含人物")
        
        # 测试验证功能
        try:
            result = await analyzer.analyze_single_user_photo("user_photo.jpg")
            print(f"分析成功:")
            print(f"肤色类型: {result.skin_tone.tone_type}")
            print(f"体型特征: {result.body_type.overall}")
            print(f"置信度: {result.confidence_score}")
        except ValueError as e:
            print(f"图片验证失败: {e}")

if __name__ == "__main__":
    asyncio.run(example_usage())