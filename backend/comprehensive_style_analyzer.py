import json
import asyncio
import logging
from typing import List, Optional, Union
from datetime import datetime
import uuid

from doubao_client import DoubaoClient, ChatMessage, MessageRole
from models.response_models import (
    StyleAnalysisResult, UserAnalysisResult, TextAnalysisResult,
    FinalRecommendationResult, ComprehensiveAnalysisResult
)
from style_image_analyzer import StyleImageAnalyzer
from user_photo_analyzer import UserPhotoAnalyzer
from text_requirement_parser import TextRequirementParser

logger = logging.getLogger(__name__)

class ImageValidationError(Exception):
    """图片验证失败的自定义异常"""
    def __init__(self, message: str, image_type: str = "unknown", details: dict = None):
        super().__init__(message)
        self.image_type = image_type
        self.details = details or {}

class ComprehensiveStyleAnalyzer:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seed-1-6-250615"):
        self.client = doubao_client
        self.model_name = model_name
        self.style_analyzer = StyleImageAnalyzer(doubao_client, model_name)
        self.user_analyzer = UserPhotoAnalyzer(doubao_client, model_name)
        self.text_parser = TextRequirementParser(doubao_client, model_name)
    
    async def analyze_comprehensive(
        self,
        style_image_paths: Optional[List[str]] = None,
        user_image_paths: Optional[List[str]] = None,
        text_requirements: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ComprehensiveAnalysisResult:
        """
        综合分析用户的时尚需求并生成个性化推荐
        
        Args:
            style_image_paths: 风格参考图片本地路径列表
            user_image_paths: 用户照片本地路径列表
            text_requirements: 用户文字需求
            session_id: 会话ID
            
        Returns:
            ComprehensiveAnalysisResult: 综合分析结果
            
        Raises:
            ImageValidationError: 当图片内容不适合分析时
            ValueError: 当没有提供任何有效输入时
        """
        if not any([style_image_paths, user_image_paths, text_requirements]):
            raise ValueError("至少需要提供一种输入类型（风格图片、用户照片或文字需求）")
        
        session_id = session_id or str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        logger.info(f"开始综合分析，会话ID: {session_id}")
        
        # Step 1: 并行执行各模块分析（带验证）
        style_result = None
        user_result = None
        text_result = None
        
        tasks = []
        
        if style_image_paths:
            tasks.append(self._analyze_style_images_safe(style_image_paths))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
            
        if user_image_paths:
            tasks.append(self._analyze_user_photos_safe(user_image_paths))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
            
        if text_requirements:
            tasks.append(self._parse_text_requirements_safe(text_requirements))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
        
        # 等待所有分析完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        style_result, user_result, text_result = results
        
        # 处理验证异常
        validation_errors = []
        for i, result in enumerate(results):
            if isinstance(result, ImageValidationError):
                error_type = ["风格图片", "用户照片", "文字需求"][i]
                validation_errors.append(f"{error_type}: {str(result)}")
                logger.error(f"{error_type}验证失败: {result}")
            elif isinstance(result, Exception):
                error_type = ["风格图片", "用户照片", "文字需求"][i]
                logger.error(f"{error_type}分析失败: {result}")
        
        # 如果有图片验证失败，抛出综合错误
        if validation_errors:
            error_message = "图片内容验证失败：\n" + "\n".join(validation_errors)
            raise ImageValidationError(error_message, "综合验证", {
                "validation_errors": validation_errors,
                "session_id": session_id
            })
        
        # 检查是否至少有一个分析成功
        if not any([style_result, user_result, text_result]):
            raise ValueError("所有分析模块都失败了，无法生成推荐")
        
        # Step 2: 生成最终推荐
        final_recommendation = None
        if any([style_result, user_result, text_result]):
            try:
                final_recommendation = await self._generate_final_recommendation(
                    style_result, user_result, text_result
                )
            except Exception as e:
                logger.error(f"生成最终推荐失败: {e}")
        
        # 构建综合结果
        result = ComprehensiveAnalysisResult()
        result.style_analysis = style_result
        result.user_analysis = user_result
        result.text_analysis = text_result
        result.final_recommendation = final_recommendation
        result.analysis_timestamp = timestamp
        result.session_id = session_id
        
        print(result)
        logger.info(f"综合分析完成，会话ID: {session_id}")
        return result
    
    async def _analyze_style_images_safe(self, image_paths: List[str]) -> Optional[StyleAnalysisResult]:
        """安全地分析风格图片"""
        try:
            return await self.style_analyzer.analyze_style_images(image_paths)
        except ValueError as e:
            # 这是图片验证失败的错误，重新抛出为ImageValidationError
            raise ImageValidationError(str(e), "style_images", {
                "image_paths": image_paths,
                "original_error": str(e)
            })
        except Exception as e:
            logger.error(f"风格图片分析失败: {e}")
            return None
    
    async def _analyze_user_photos_safe(self, image_paths: List[str]) -> Optional[UserAnalysisResult]:
        """安全地分析用户照片"""
        try:
            return await self.user_analyzer.analyze_user_photos(image_paths)
        except ValueError as e:
            # 这是图片验证失败的错误，重新抛出为ImageValidationError
            raise ImageValidationError(str(e), "user_photos", {
                "image_paths": image_paths,
                "original_error": str(e)
            })
        except Exception as e:
            logger.error(f"用户照片分析失败: {e}")
            return None
    
    async def _parse_text_requirements_safe(self, text: str) -> Optional[TextAnalysisResult]:
        """安全地解析文字需求"""
        try:
            return await self.text_parser.parse_text_requirements(text)
        except Exception as e:
            logger.error(f"文字需求解析失败: {e}")
            return None
    
    async def _generate_final_recommendation(
        self,
        style_result: Optional[StyleAnalysisResult],
        user_result: Optional[UserAnalysisResult],
        text_result: Optional[TextAnalysisResult]
    ) -> FinalRecommendationResult:
        """
        基于所有分析结果生成最终推荐
        """
        # 构建综合分析的prompt
        prompt = self._build_comprehensive_prompt(style_result, user_result, text_result)
        
        messages = [
            ChatMessage(
                role=MessageRole.USER,
                content=prompt
            )
        ]
        
        # 调用API生成推荐
        response = await self.client.create_chat_completion(
            model=self.model_name,
            messages=messages,
            temperature=0.3,  # 稍高的创造性，但保持逻辑性
            max_tokens=4096
        )
        
        # 解析响应
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"综合推荐API响应: {response_text}")
        
        # 清理markdown格式
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # 解析JSON
        try:
            result_dict = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"综合推荐JSON解析失败: {e}, 响应内容: {response_text}")
            raise ValueError(f"AI返回的综合推荐格式不正确: {e}")
        
        # 转换为结构化对象
        result = FinalRecommendationResult(**result_dict)
        
        # 计算整体置信度
        result.overall_confidence = self._calculate_overall_confidence(
            style_result, user_result, text_result, result
        )
        
        return result
    
    def _build_comprehensive_prompt(
        self,
        style_result: Optional[StyleAnalysisResult],
        user_result: Optional[UserAnalysisResult],
        text_result: Optional[TextAnalysisResult]
    ) -> str:
        """
        构建综合分析的prompt
        """
        prompt = """你是一位顶级的时尚顾问和个人形象设计师。现在需要基于用户的多维信息，生成个性化的服装推荐方案。

请仔细分析以下信息：

"""
        
        # 添加风格分析结果
        if style_result:
            prompt += f"""## 1. 风格参考分析：
用户想要的风格：{style_result.overall_style}
风格关键词：{', '.join(style_result.style_keywords)}
色彩方案：{style_result.color_scheme.primary_colors}，{style_result.color_scheme.color_mood}
适合场合：{', '.join(style_result.occasions)}
风格描述：{style_result.style_description}

"""
        else:
            prompt += """## 1. 风格参考分析：
用户未提供风格参考图片，请基于其他信息推荐适合的风格。

"""
        
        # 添加用户分析结果
        if user_result:
            prompt += f"""## 2. 用户个人分析：
体型特征：{user_result.body_type.overall}
身材比例：{user_result.body_type.proportions}
适合版型：{', '.join(user_result.body_type.best_silhouettes)}
肤色类型：{user_result.skin_tone.tone_type}
适合颜色：{', '.join(user_result.skin_tone.suitable_colors)}
避免颜色：{', '.join(user_result.skin_tone.avoid_colors)}
脸型：{user_result.face_shape.shape}
适合领型：{', '.join(user_result.face_shape.suitable_necklines)}
个人气质：{user_result.personal_style.temperament}
推荐风格：{', '.join(user_result.personal_style.recommended_styles)}

"""
        else:
            prompt += """## 2. 用户个人分析：
用户未提供个人照片，请基于其他信息和常见情况给出通用建议。

"""
        
        # 添加文字需求分析结果
        if text_result:
            prompt += f"""## 3. 文字需求解析：
目标场合：{text_result.occasion or '未明确'}
喜欢的风格：{', '.join(text_result.style_preferences.liked_styles) if text_result.style_preferences.liked_styles else '未明确'}
不喜欢的风格：{', '.join(text_result.style_preferences.disliked_styles) if text_result.style_preferences.disliked_styles else '未明确'}
预算范围：{text_result.budget.range or '未明确'}
消费水平：{text_result.budget.level or '未明确'}
特殊要求：{', '.join(text_result.special_requirements) if text_result.special_requirements else '无'}
情感基调：{text_result.emotional_tone or '中性'}
优先需求：{text_result.priority or '未明确'}

"""
        else:
            prompt += """## 3. 文字需求解析：
用户未提供具体的文字需求，请基于风格和个人分析给出综合建议。

"""
        
        prompt += """## 综合分析任务：
请基于以上信息进行深度分析和推荐：

1. **兼容性分析**：分析用户想要的风格与个人条件的匹配度（1-10分）
2. **优势与调整**：指出用户的条件优势，以及需要调整的地方
3. **推荐方案**：生成3套不同风格的搭配方案：
   - 保守方案：安全、易于接受的搭配
   - 平衡方案：在适合基础上适度突破的搭配
   - 大胆方案：更有个性和前卫感的搭配
4. **每套方案要求**：
   - 包含上衣、下装、鞋子、配饰等具体单品
   - 详细说明每个单品的选择理由
   - 预测用户对该方案的接受度
5. **购物指导**：提供购物优先级和搭配技巧

请严格按照以下JSON格式返回，不要包含任何其他文字：

{
  "compatibility_analysis": {
    "match_score": 8.5,
    "strengths": ["优势1", "优势2", "优势3"],
    "adjustments": ["调整建议1", "调整建议2"]
  },
  "outfit_recommendations": [
    {
      "theme": "保守方案",
      "items": [
        {
          "category": "上衣",
          "description": "白色基础款衬衫",
          "color": "白色",
          "style": "修身版型",
          "why_suitable": "适合肤色，突出身材优势"
        }
      ],
      "overall_effect": "整体效果描述",
      "acceptance_prediction": "高",
      "styling_tips": ["搭配技巧1", "搭配技巧2"]
    }
  ],
  "shopping_priority": ["优先购买单品1", "优先购买单品2"],
  "styling_tips": ["通用搭配建议1", "通用搭配建议2"],
  "confidence_boost": "这些搭配将如何提升用户自信的详细说明"
}

请确保推荐方案实用、可行，并充分考虑用户的个人条件和需求。"""
        
        return prompt
    
    def _calculate_overall_confidence(
        self,
        style_result: Optional[StyleAnalysisResult],
        user_result: Optional[UserAnalysisResult],
        text_result: Optional[TextAnalysisResult],
        final_result: FinalRecommendationResult
    ) -> float:
        """
        计算整体推荐的置信度
        """
        confidence = 0.5  # 基础置信度
        
        # 根据输入信息的完整性调整
        if style_result:
            confidence += 0.15 * (style_result.confidence_score or 0.7)
        
        if user_result:
            confidence += 0.2 * (user_result.confidence_score or 0.7)
        
        if text_result:
            confidence += 0.15 * (text_result.confidence_score or 0.7)
        
        # 根据推荐方案的完整性调整
        if final_result.outfit_recommendations:
            if len(final_result.outfit_recommendations) >= 3:
                confidence += 0.1
            confidence += min(0.1, len(final_result.outfit_recommendations) * 0.03)
        
        # 根据兼容性分析的匹配度调整
        if final_result.compatibility_analysis.match_score:
            score_factor = final_result.compatibility_analysis.match_score / 10
            confidence += 0.1 * score_factor
        
        return min(confidence, 1.0)


# 使用示例
async def example_usage():
    async with DoubaoClient() as client:
        analyzer = ComprehensiveStyleAnalyzer(client)
        
        try:
            # 完整的综合分析示例
            result = await analyzer.analyze_comprehensive(
                style_image_paths=["style1.jpg", "style2.jpg"],
                user_image_paths=["user_photo.jpg"],
                text_requirements="我是一个身高165，体重50kg，年龄25岁的学生。我想知道我去参加朋友的生日聚会应该怎么穿。"
            )
            
            print(f"分析完成！")
            print(f"会话ID: {result.session_id}")
            print(f"整体置信度: {result.final_recommendation.overall_confidence if result.final_recommendation else 'N/A'}")
            
        except ImageValidationError as e:
            print(f"图片验证失败: {e}")
            print(f"错误详情: {e.details}")
        except ValueError as e:
            print(f"输入验证失败: {e}")

if __name__ == "__main__":
    asyncio.run(example_usage())