import json
import asyncio
import logging
from typing import Optional, Dict, Any
from doubao_client import DoubaoClient, ChatMessage, MessageRole
from models.response_models import ComprehensiveAnalysisResult
from datetime import datetime

logger = logging.getLogger(__name__)

class PersonalizedResponseGenerator:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seed-1-6-250615"):
        self.client = doubao_client
        self.model_name = model_name
    
    async def generate_personalized_response(
        self, 
        analysis_result: ComprehensiveAnalysisResult,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        基于综合分析结果生成个性化的、适合年轻人的回复
        
        Args:
            analysis_result: 综合分析结果
            user_name: 用户名称（可选）
            
        Returns:
            Dict: 包含个性化回复内容的字典
        """
        try:
            logger.info("开始生成个性化回复")
            
            # 检查分析结果的完整性
            if not analysis_result:
                return self._generate_error_response("分析结果为空", user_name)
            
            # 检查是否有有效的分析数据
            has_valid_data = any([
                analysis_result.style_analysis,
                analysis_result.user_analysis,
                analysis_result.text_analysis,
                analysis_result.final_recommendation
            ])
            
            if not has_valid_data:
                return self._generate_no_data_response(user_name)
            
            # 构建分析摘要
            analysis_summary = self._build_analysis_summary(analysis_result)
            
            # 构建个性化prompt
            prompt = self._build_personalized_prompt(analysis_summary, user_name)
            
            # 调用大模型生成回复
            messages = [
                ChatMessage(
                    role=MessageRole.USER,
                    content=prompt
                )
            ]
            
            response = await self.client.create_chat_completion(
                model=self.model_name,
                messages=messages,
                temperature=0.8,  # 较高的创造性，让回复更生动
                max_tokens=3000
            )
            
            # 直接获取回复文本
            personalized_text = response.choices[0].message.content.strip()
            logger.debug(f"个性化回复生成完成，长度: {len(personalized_text)}")
            print(personalized_text)
            # 返回结构化数据，但主要内容就是文本
            return {
                "content": personalized_text,
                "session_id": analysis_result.session_id,
                "generated_at": datetime.now().isoformat(),
                "analysis_confidence": self._calculate_overall_confidence(analysis_result),
                "user_name": user_name
            }
            
        except Exception as e:
            logger.error(f"生成个性化回复失败: {str(e)}")
            # 返回一个友好的错误回复
            fallback_response = self._generate_fallback_response(user_name)
            return {
                "content": fallback_response,
                "session_id": analysis_result.session_id if analysis_result else "unknown",
                "generated_at": datetime.now().isoformat(),
                "analysis_confidence": 0.7,
                "user_name": user_name,
                "error_handled": True
            }
    
    def _generate_error_response(self, error_msg: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        """生成错误情况下的回复"""
        name_part = f"{user_name}，" if user_name else ""
        
        error_response = f"""嘿{name_part}看起来系统在分析过程中遇到了一些小问题呢～

不过别担心！这种情况偶尔会发生。你可以：

✨ **重新尝试一下**
- 检查上传的图片是否清晰
- 确保图片包含你想要的穿搭风格或个人照片
- 可以尝试重新描述一下你的需求

🌟 **小贴士**
- 风格图片最好选择有明显穿搭展示的照片
- 个人照片建议使用清晰可见的全身或半身照
- 文字描述可以包含场合、喜好、预算等信息

相信下次一定能为你生成完美的时尚建议！有任何问题随时找我哦～ 💕"""

        return {
            "content": error_response,
            "session_id": "error_session",
            "generated_at": datetime.now().isoformat(),
            "analysis_confidence": 0.5,
            "user_name": user_name,
            "error_handled": True
        }
    
    def _generate_no_data_response(self, user_name: Optional[str] = None) -> Dict[str, Any]:
        """生成无有效数据时的回复"""
        name_part = f"{user_name}，" if user_name else ""
        
        no_data_response = f"""嘿{name_part}谢谢你信任我来帮你分析时尚风格！✨

不过我发现你提供的信息可能还不够充分，让我无法给出精准的建议呢～

为了给你最棒的时尚建议，建议你：

📸 **上传合适的图片**
- **风格参考**：选择你喜欢的穿搭照片、街拍图或时尚博主的搭配
- **个人照片**：上传你的清晰照片，最好是全身或半身照

✍️ **描述具体需求**
- 想要搭配的场合（约会、工作、聚会等）
- 个人喜好和风格偏向
- 预算范围和特殊要求

💡 **举个例子**
"我想要参加朋友生日聚会的穿搭，喜欢韩系风格，预算1000元以内，希望看起来活泼可爱一些～"

重新来试试吧！我相信能为你打造出超棒的时尚方案～ 🎀"""

        return {
            "content": no_data_response,
            "session_id": "no_data_session",
            "generated_at": datetime.now().isoformat(),
            "analysis_confidence": 0.6,
            "user_name": user_name,
            "guidance_provided": True
        }
    
    def _build_analysis_summary(self, result: ComprehensiveAnalysisResult) -> str:
        """构建分析结果摘要"""
        summary_parts = []
        
        # 风格分析摘要
        if result.style_analysis:
            style = result.style_analysis
            summary_parts.append(f"""
## 喜欢的风格分析：
- 整体风格：{style.overall_style}
- 风格关键词：{', '.join(style.style_keywords)}
- 色彩偏好：{style.color_scheme.primary_colors}，{style.color_scheme.color_mood}
- 适合场合：{', '.join(style.occasions)}
- 风格描述：{style.style_description}
""")
        
        # 用户个人分析摘要
        if result.user_analysis:
            user = result.user_analysis
            summary_parts.append(f"""
## 个人特征分析：
- 体型特征：{user.body_type.overall}
- 身材比例：{user.body_type.proportions}
- 适合版型：{', '.join(user.body_type.best_silhouettes)}
- 肤色类型：{user.skin_tone.tone_type}
- 适合颜色：{', '.join(user.skin_tone.suitable_colors)}
- 脸型：{user.face_shape.shape}
- 个人气质：{user.personal_style.temperament}
- 推荐风格：{', '.join(user.personal_style.recommended_styles)}
""")
        
        # 文字需求摘要
        if result.text_analysis:
            text = result.text_analysis
            summary_parts.append(f"""
## 用户需求分析：
- 目标场合：{text.occasion or '未明确'}
- 喜欢风格：{', '.join(text.style_preferences.liked_styles) if text.style_preferences.liked_styles else '未明确'}
- 预算范围：{text.budget.range or '未明确'}
- 特殊要求：{', '.join(text.special_requirements) if text.special_requirements else '无'}
- 优先需求：{text.priority or '未明确'}
""")
        
        # 最终推荐摘要
        if result.final_recommendation:
            final = result.final_recommendation
            summary_parts.append(f"""
## 推荐分析：
- 匹配度评分：{final.compatibility_analysis.match_score}/10
- 用户优势：{', '.join(final.compatibility_analysis.strengths)}
- 推荐方案数：{len(final.outfit_recommendations)}套
- 购物优先级：{', '.join(final.shopping_priority)}
""")
        
        return '\n'.join(summary_parts)
    
    def _build_personalized_prompt(self, analysis_summary: str, user_name: Optional[str] = None) -> str:
        """构建个性化prompt"""
        name_part = f"，{user_name}" if user_name else ""
        
        return f"""
你是一位超级懂年轻人的时尚博主和心理分析师。现在需要基于用户的时尚分析结果，写一份个性化的时尚建议回复，就像在和好朋友聊天一样。

你的人设特点：
- 🌟 年轻、时尚、有趣的时尚博主
- 🧠 懂心理学，能从穿搭看出性格和MBTI类型
- 💬 语言风格活泼亲切，偶尔用点网络流行语和emoji
- 💝 善于鼓励和赞美，让用户感到自信和被理解
- ✨ 专业但不古板，像闺蜜一样贴心

用户分析结果：
{analysis_summary}

请写一份个性化的时尚建议回复{name_part}，内容要包括：

## 📝 内容要求：
1. **热情开场**：亲切有趣的问候，表达对用户品味的赞美
2. **性格&气质分析**：从穿搭偏好分析用户性格，可以推测MBTI类型，解读生活态度
3. **穿衣品味解读**：评价用户的时尚水平，解读风格偏好背后的个性
4. **具体穿搭建议**：给出实用的搭配方案，包括单品推荐和搭配理由
5. **色彩&购物指导**：推荐适合的颜色搭配，给出购物优先级建议
6. **信心加持**：鼓励用户，让TA感到自己很棒很有魅力
7. **温暖结尾**：邀请继续交流，表达支持和关心

## 🎨 语言风格要求：
- 口语化、年轻化，就像闺蜜在聊天
- 适当使用emoji表情，让回复更生动
- 可以用一些网络流行语，但不要过度
- 语调积极正面，充满正能量
- 让用户感到被理解、被欣赏、被支持
- 专业建议要通俗易懂，避免太技术化的词汇

## 💡 写作提示：
- 想象你是用户最好的闺蜜，既专业又贴心
- 每个建议都要说明"为什么"，让用户明白道理
- 适当分享一些时尚小贴士或趣味知识
- 让整个回复读起来温暖、有趣、实用

请直接写这份个性化回复，不要用任何格式标记或结构化标签，就是一段自然流畅的对话文本。目标是让用户读完后感觉"这个时尚顾问真的很懂我！"并且获得实用的穿搭灵感。

字数控制在800-1200字左右，让回复既详细又不会太冗长。
"""
    
    def _calculate_overall_confidence(self, result: ComprehensiveAnalysisResult) -> float:
        """计算整体分析信心度"""
        confidence_factors = []
        
        if result.style_analysis and result.style_analysis.confidence_score:
            confidence_factors.append(result.style_analysis.confidence_score)
        
        if result.user_analysis and result.user_analysis.confidence_score:
            confidence_factors.append(result.user_analysis.confidence_score)
        
        if result.text_analysis and result.text_analysis.confidence_score:
            confidence_factors.append(result.text_analysis.confidence_score)
        
        if result.final_recommendation and result.final_recommendation.overall_confidence:
            confidence_factors.append(result.final_recommendation.overall_confidence)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.7  # 默认信心度
    
    def _generate_fallback_response(self, user_name: Optional[str] = None) -> str:
        """生成备用回复（当出现错误时使用）"""
        name_part = f"{user_name}，" if user_name else ""
        
        return f"""嘿{name_part}虽然刚才在分析你的时尚风格时遇到了一点小状况，但我从你的选择中已经能感受到你的独特品味啦！✨

你能想到来寻求时尚建议，说明你是一个很有自我意识、愿意提升自己的人。这种积极的态度本身就很棒！💕

无论你现在的穿搭风格是什么样的，记住最重要的是：
🌟 穿出自信的自己
🌟 选择让你感到舒适快乐的衣服  
🌟 不要害怕尝试新的搭配

时尚本来就是一个探索和表达自我的过程，没有标准答案，只有最适合你的那一套。相信你的直觉，保持好奇心，你一定能找到属于自己的独特风格！

如果你想继续聊聊穿搭的话题，我随时都在这里支持你哦～ 💪✨"""

    async def generate_image_validation_error_response(
        self, 
        error_details: Dict[str, Any],
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        为图片验证失败生成专门的回复
        
        Args:
            error_details: 错误详情，包含验证失败的具体信息
            user_name: 用户名称
            
        Returns:
            Dict: 包含友好错误回复的字典
        """
        name_part = f"{user_name}，" if user_name else ""
        
        # 根据错误类型生成不同的回复
        if "风景图片" in str(error_details) or "食物图片" in str(error_details):
            content = f"""嘿{name_part}我看了你刚才上传的图片，发现可能不太适合做时尚分析呢～ 😅

看起来你上传的图片可能是风景、美食或其他类型的照片，但我需要的是：

🎯 **风格参考图片**：
- 时尚博主的穿搭照片
- 街拍中喜欢的搭配
- 杂志上的时尚造型
- 明星或网红的穿搭展示

👤 **个人照片**：
- 你的清晰全身照或半身照
- 能看到脸型和身材比例的照片
- 日常生活照也可以哦

💡 **小贴士**：我是专门分析时尚穿搭的AI，需要能看到服装和人物的图片才能给你最准确的建议呢！

重新上传合适的图片，我就能为你打造专属的时尚方案啦～ ✨"""

        elif "无人物" in str(error_details) or "模糊不清" in str(error_details):
            content = f"""嘿{name_part}我看了你上传的个人照片，但好像没有很清楚地看到你呢～ 🤔

为了给你最准确的个人形象分析，我需要：

📸 **清晰的人物照片**：
- 能看到你脸部特征的照片
- 最好是全身或半身照
- 光线充足、不要太模糊
- 你是照片的主要内容

✨ **为什么需要这样**：
只有看清楚你的肤色、脸型、身材比例，我才能推荐最适合你的颜色搭配和服装版型呀！

💝 **别担心**：
不需要特别精美的照片，日常自拍或生活照都可以！重要的是能看清你的基本特征就行～

重新上传一张清晰的照片，让我好好看看你，然后为你量身定制时尚建议吧！ 🌟"""

        else:
            content = f"""嘿{name_part}在分析你的图片时遇到了一些小问题，可能是图片内容不太适合时尚分析呢～

让我帮你重新梳理一下需要什么样的图片：

🎨 **风格参考（你喜欢的穿搭）**：
- 包含明显服装展示的图片
- 时尚博主、明星的穿搭照
- 你在网上看到喜欢的搭配

👤 **个人照片（你自己的照片）**：
- 能看到你本人的清晰照片
- 最好是全身或半身照
- 日常生活照也完全OK

💡 **温馨提示**：
我是专业的时尚分析师，但只能分析与服装、穿搭、人物形象相关的内容哦！

重新来试试吧，我相信这次一定能为你生成超棒的时尚建议！ ✨💕"""

        return {
            "content": content,
            "session_id": "validation_error",
            "generated_at": datetime.now().isoformat(),
            "analysis_confidence": 0.8,
            "user_name": user_name,
            "error_type": "image_validation_failed",
            "guidance_provided": True
        }


# 使用示例
async def example_usage():
    """使用示例"""
    async with DoubaoClient() as client:
        generator = PersonalizedResponseGenerator(client)
        
        print("个性化回复生成器已准备就绪！")
        print("现在支持图片验证失败的友好错误处理")

if __name__ == "__main__":
    asyncio.run(example_usage())