import json
import asyncio
import logging
from typing import Optional
from doubao_client import DoubaoClient, ChatMessage, MessageRole
from models.response_models import TextAnalysisResult
from prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)

class TextRequirementParser:
    def __init__(self, doubao_client: DoubaoClient, model_name: str = "doubao-seed-1-6-250615"):
        self.client = doubao_client
        self.model_name = model_name
        self.prompt_template = PromptTemplates()
    
    async def parse_text_requirements(self, user_input: str) -> TextAnalysisResult:
        """
        解析用户的文字需求
        
        Args:
            user_input: 用户输入的文字需求
            
        Returns:
            TextAnalysisResult: 文字需求分析结果
        """
        try:
            if not user_input or not user_input.strip():
                raise ValueError("用户输入不能为空")
            
            logger.info(f"开始解析文字需求: {user_input[:50]}...")
            
            # 构建消息
            prompt = self.prompt_template.get_text_analysis_prompt(user_input.strip())
            messages = [
                ChatMessage(
                    role=MessageRole.USER,
                    content=prompt
                )
            ]
            
            # 调用API
            response = await self.client.create_chat_completion(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # 很低的随机性，确保结构化输出稳定
                max_tokens=1024
            )
            
            # 解析响应
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"API响应: {response_text}")
            
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
            
            # 转换为结构化对象
            result = TextAnalysisResult(**result_dict)
            result.confidence_score = self._calculate_confidence_score(result, user_input)
            
            logger.info(f"文字需求解析完成，场合: {result.occasion}, 优先级: {result.priority}")
            print(result)
            return result
            
        except Exception as e:
            logger.error(f"文字需求解析失败: {str(e)}")
            raise
    
    def _calculate_confidence_score(self, result: TextAnalysisResult, original_input: str) -> float:
        """
        计算分析结果的置信度
        """
        score = 0.7  # 基础分数
        
        # 输入长度影响置信度
        if len(original_input) > 20:
            score += 0.1
        
        # 提取到明确场合，增加置信度
        if result.occasion:
            score += 0.1
        
        # 提取到预算信息，增加置信度
        if result.budget.range or result.budget.level:
            score += 0.05
        
        # 提取到风格偏好，增加置信度
        if result.style_preferences.liked_styles:
            score += 0.05
        
        return min(score, 1.0)


# 使用示例
async def example_usage():
    async with DoubaoClient() as client:
        parser = TextRequirementParser(client)
        
        test_inputs = [
            "我是一个身高182，体重60kg，年龄25岁的学生。我想知道我去参加朋友的生日聚会应该怎么穿。我的预算是所有加起来不超过1500，目前的季节是10月份秋天，我喜欢活泼和干净的风格",
        ]
        
        for user_input in test_inputs:
            result = await parser.parse_text_requirements(user_input)
            print(result)

if __name__ == "__main__":
    asyncio.run(example_usage())