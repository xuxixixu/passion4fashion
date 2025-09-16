import json
import asyncio
import logging
import os
import base64
import mimetypes
from typing import List, Union, Optional
from doubao_client import DoubaoClient, ChatMessage, MessageRole, MessageContent, MessageContentType
from models.response_models import StyleAnalysisResult
from prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)

class StyleImageAnalyzer:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seed-1-6-250615"):
        self.client = doubao_client
        self.model_name = model_name
        self.prompt_template = PromptTemplates()
    
    async def analyze_style_images(
        self, 
        image_paths: List[str],
        detail_level: str = "auto"
    ) -> StyleAnalysisResult:
        """
        分析一张或多张风格图片
        
        Args:
            image_paths: 本地图片文件路径列表
            detail_level: 图片分析详细程度 ("low", "high", "auto")
            
        Returns:
            StyleAnalysisResult: 风格分析结果
        """
        try:
            if not image_paths:
                raise ValueError("至少需要提供一张图片")
            
            logger.info(f"开始分析 {len(image_paths)} 张风格图片")
            
            # 验证文件存在
            for path in image_paths:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"图片文件不存在: {path}")
            
            # 第一步：验证图片内容是否适合风格分析
            validation_result = await self._validate_style_images(image_paths, detail_level)
            if not validation_result["is_valid"]:
                # 如果图片不合适，抛出具体的错误
                raise ValueError(f"图片内容不适合风格分析: {validation_result['reason']}")
            
            # 第二步：进行具体的风格分析
            return await self._perform_style_analysis(image_paths, detail_level)
            
        except Exception as e:
            logger.error(f"风格图片分析失败: {str(e)}")
            raise

    async def _validate_style_images(self, image_paths: List[str], detail_level: str) -> dict:
        """
        验证图片是否包含适合风格分析的内容
        
        Returns:
            dict: {"is_valid": bool, "reason": str, "content_type": str}
        """
        try:
            logger.info("正在验证图片内容是否适合风格分析...")
            
            # 构建验证消息内容
            content_list = []
            
            # 添加验证prompt
            validation_prompt = self._get_style_validation_prompt(len(image_paths))
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
            logger.debug(f"图片验证API响应: {response_text}")
            
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
                logger.error(f"验证结果JSON解析失败: {e}, 响应内容: {response_text}")
                # 如果解析失败，默认允许通过，避免误杀
                return {
                    "is_valid": True,
                    "reason": "验证服务异常，默认通过",
                    "content_type": "unknown",
                    "confidence": 0.5
                }
            
            logger.info(f"图片验证结果: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"图片内容验证失败: {str(e)}")
            # 验证失败时默认通过，避免影响正常功能
            return {
                "is_valid": True,
                "reason": f"验证过程异常: {str(e)}",
                "content_type": "unknown",
                "confidence": 0.5
            }
    
    def _get_style_validation_prompt(self, image_count: int) -> str:
        """获取风格图片验证的prompt"""
        image_instruction = f"这{image_count}张图片" if image_count > 1 else "这张图片"
        
        return f"""
你是一位专业的图片内容识别专家。请判断{image_instruction}是否适合进行时尚风格分析。

请仔细观察{image_instruction}，判断是否包含以下风格分析所需的内容：
✅ 合适的内容包括：
- 人物穿搭照片（全身或半身）
- 服装单品展示图
- 时尚搭配示范图
- 街拍穿搭图片
- 时尚杂志图片
- 模特展示服装的图片
- 明显的服装、配饰展示

❌ 不合适的内容包括：
- 纯风景照片
- 食物图片
- 动物图片
- 建筑物图片
- 抽象艺术图片
- 文字图片
- 没有明显服装元素的图片
- 非人物时尚相关的图片

评判标准：
1. 图片主体是否与时尚、服装、穿搭相关
2. 是否能从中提取到有意义的风格信息
3. 是否适合作为时尚推荐的参考

请用以下JSON格式返回判断结果，不要包含任何其他文字：
{{
  "is_valid": true/false,
  "reason": "详细说明判断原因",
  "content_type": "服装展示/人物穿搭/风景照片/食物图片/其他",
  "confidence": 0.95,
  "main_elements": ["图片中的主要元素1", "主要元素2"],
  "suitable_for_analysis": "说明是否适合风格分析及原因"
}}

如果图片不包含任何时尚、服装、穿搭相关内容，请将is_valid设置为false。
"""
    
    async def _perform_style_analysis(self, image_paths: List[str], detail_level: str) -> StyleAnalysisResult:
        """执行具体的风格分析"""
        logger.info("开始执行具体的风格分析...")
        
        # 构建消息内容
        content_list = []
        
        # 添加原有的风格分析prompt
        prompt = self.prompt_template.get_style_analysis_prompt(len(image_paths))
        content_list.append(MessageContent(type=MessageContentType.TEXT, text=prompt))
        
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
            logger.debug(f"添加第 {i+1} 张图片: {image_path}")
        
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
            temperature=0.3,  # 降低随机性，提高一致性
            max_tokens=2048
        )
        
        # 解析响应
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"风格分析API响应: {response_text}")
        
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
        result_dict = self._normalize_analysis_result(result_dict)
        
        # 转换为结构化对象
        try:
            result = StyleAnalysisResult(**result_dict)
        except Exception as e:
            logger.error(f"数据模型验证失败: {e}, 数据内容: {result_dict}")
            raise ValueError(f"AI返回的数据格式不符合预期: {e}")
        
        result.confidence_score = self._calculate_confidence_score(result)
        logger.info(f"风格分析完成，识别风格: {result.overall_style}")
        print(result)
        return result
    
    def _calculate_confidence_score(self, result: StyleAnalysisResult) -> float:
        """
        计算分析结果的置信度
        """
        score = 0.7  # 基础分数
        
        # 如果有详细的服装单品信息，增加置信度
        if result.clothing_items and len(result.clothing_items) > 0:
            score += 0.1
        
        # 如果有风格关键词，增加置信度
        if result.style_keywords and len(result.style_keywords) >= 3:
            score += 0.1
        
        # 如果有详细的风格描述，增加置信度
        if result.style_description and len(result.style_description) > 20:
            score += 0.1
        
        return min(score, 1.0)
    
    def _normalize_analysis_result(self, result_dict: dict) -> dict:
        """
        标准化AI返回的分析结果，处理可能的格式问题
        """
        try:
            # 处理season字段：如果是列表，转换为字符串
            if "season" in result_dict and isinstance(result_dict["season"], list):
                result_dict["season"] = "、".join(result_dict["season"])
                logger.debug(f"转换season字段从列表到字符串: {result_dict['season']}")
            
            # 处理occasions字段：确保是列表
            if "occasions" in result_dict and isinstance(result_dict["occasions"], str):
                result_dict["occasions"] = [result_dict["occasions"]]
                logger.debug(f"转换occasions字段从字符串到列表: {result_dict['occasions']}")
            
            # 处理style_keywords字段：确保是列表
            if "style_keywords" in result_dict and isinstance(result_dict["style_keywords"], str):
                result_dict["style_keywords"] = [result_dict["style_keywords"]]
                logger.debug(f"转换style_keywords字段从字符串到列表: {result_dict['style_keywords']}")
            
            # 处理color_scheme中的primary_colors字段：确保是列表
            if "color_scheme" in result_dict and "primary_colors" in result_dict["color_scheme"]:
                if isinstance(result_dict["color_scheme"]["primary_colors"], str):
                    result_dict["color_scheme"]["primary_colors"] = [result_dict["color_scheme"]["primary_colors"]]
                    logger.debug(f"转换primary_colors字段从字符串到列表")
            
            # 处理clothing_items字段：确保是列表
            if "clothing_items" in result_dict and not isinstance(result_dict["clothing_items"], list):
                result_dict["clothing_items"] = []
                logger.debug("clothing_items字段不是列表，重置为空列表")
            
            return result_dict
            
        except Exception as e:
            logger.warning(f"标准化分析结果时出现问题: {e}, 返回原始数据")
            return result_dict
    
    async def analyze_single_style_image(self, image_path: str) -> StyleAnalysisResult:
        """
        分析单张风格图片的便捷方法
        """
        return await self.analyze_style_images([image_path])


# 使用示例
async def example_usage():
    async with DoubaoClient() as client:
        analyzer = StyleImageAnalyzer(client)
        
        print("风格图片分析器已就绪！现在会先验证图片内容是否适合分析")
        
        # 测试验证功能
        try:
            result = await analyzer.analyze_single_style_image("test_image.jpg")
            print(f"分析成功: {result.overall_style}")
        except ValueError as e:
            print(f"图片验证失败: {e}")

if __name__ == "__main__":
    asyncio.run(example_usage())