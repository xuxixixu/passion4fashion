# agents/ootd_agent.py
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

from models.database_models import User, Wardrobe, ConversationMessage, OOTDSession
from models.ootd_models import UserDataSummary, OOTDRecommendation
from dotenv import load_dotenv

class DatabaseQueryTool(BaseTool):
    """数据库查询工具"""
    name: str = "database_query"
    description: str = "查询用户的个人信息和衣橱数据，用于生成个性化OOTD建议"
    
    def _run(self, user_id: int) -> str:
        """查询用户数据"""
        return self._arun(user_id)
    
    async def _arun(self, user_id: int) -> str:
        """异步查询用户数据"""
        try:
            # 查询用户信息
            user = await User.get_or_none(id=user_id)
            if not user:
                return "用户不存在"
            
            # 查询衣橱数据
            wardrobe_items = await Wardrobe.filter(user_id=user_id, is_available=True)
            
            # 构建用户数据摘要
            user_data = {
                "profile": {
                    "nickname": user.nickname,
                    "gender": user.gender,
                    "height": user.height,
                    "weight": user.weight,
                    "body_shape": user.body_shape,
                    "skin_tone": user.skin_tone,
                },
                "wardrobe": {
                    "total_items": len(wardrobe_items),
                    "items_by_type": {},
                    "items": []
                }
            }
            
            # 按类型统计衣物
            for item in wardrobe_items:
                item_type = item.type
                if item_type not in user_data["wardrobe"]["items_by_type"]:
                    user_data["wardrobe"]["items_by_type"][item_type] = 0
                user_data["wardrobe"]["items_by_type"][item_type] += 1
                
                # 添加具体衣物信息
                user_data["wardrobe"]["items"].append({
                    "id": item.id,
                    "name": item.name,
                    "type": item.type,
                    "color": item.color,
                    "brand": item.brand,
                    "material": item.material,
                    "season": item.season,
                    "occasion": item.occasion,
                    "style_tags": item.style_tags.split(",") if item.style_tags else [],
                    "wear_count": item.wear_count,
                    "is_favorite": item.is_favorite
                })
            
            return json.dumps(user_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"查询数据时发生错误：{str(e)}"

class ConversationHistoryTool(BaseTool):
    """对话历史查询工具"""
    name: str = "conversation_history"
    description: str = "获取用户最近的对话历史，了解用户的偏好和上下文"
    
    def _run(self, user_id: int, hours: int = 2) -> str:
        return self._arun(user_id, hours)
    
    async def _arun(self, user_id: int, hours: int = 2) -> str:
        """获取最近的对话历史"""
        try:
            messages = await ConversationMessage.get_recent_messages(user_id, hours)
            
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.text_content,
                    "time": msg.created_at.isoformat(),
                    "conversation_id": msg.conversation_id
                })
            
            return json.dumps(history, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"获取对话历史时发生错误：{str(e)}"

class OOTDAgent:
    """OOTD智能助手"""
    
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model="openai/gpt-5",
            temperature=0.7,
            openai_api_key=openai_api_key
        )
        
        # 初始化工具
        self.tools = [
            DatabaseQueryTool(),
            ConversationHistoryTool(),
        ]
        
        # 创建提示模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 创建agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True
        )
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个专业的OOTD时尚助手，你的任务是：

1. **理解用户需求**：
   - 仔细分析用户的穿搭需求和场景
   - 如果用户的问题不够具体，主动询问详细信息（场合、天气、心情、风格偏好等）

2. **个性化分析**：
   - 当需要个性化推荐时，使用database_query工具获取用户的身材数据和衣橱信息
   - 根据用户的体型、肤色、已有衣物进行分析
   - 考虑用户的历史偏好和穿搭习惯

3. **专业建议**：
   - 提供具体的搭配建议，包括颜色、款式、配饰等
   - 解释推荐理由，包括为什么这样搭配适合用户
   - 考虑实用性：天气、场合、舒适度等因素

4. **互动交流**：
   - 保持友好、专业的语气
   - 鼓励用户提供更多信息以获得更好的建议
   - 可以询问用户对建议的反馈，并据此调整

5. **工具使用**：
   - 只有在需要用户个人数据时才调用database_query
   - 在需要了解用户历史偏好时使用conversation_history
   - 如果问题是通用的时尚咨询，无需调用工具

记住，你的目标是帮助用户找到最适合的穿搭方案，让他们在任何场合都自信美丽！"""

    async def chat(self, user_id: int, message: str, chat_history: List[BaseMessage] = None) -> Dict[str, Any]:
        """处理用户消息"""
        if chat_history is None:
            chat_history = []
        
        try:
            result = await self.executor.ainvoke({
                "input": message,
                "chat_history": chat_history,
                "user_id": user_id
            })
            
            return {
                "response": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "user_data_used": any("database_query" in str(step) for step in result.get("intermediate_steps", []))
            }
            
        except Exception as e:
            return {
                "response": f"抱歉，处理您的请求时遇到了问题：{str(e)}",
                "intermediate_steps": [],
                "user_data_used": False
            }

    async def get_ootd_recommendation(self, user_id: int, requirements: str) -> OOTDRecommendation:
        """获取OOTD推荐"""
        # 获取用户数据
        db_tool = DatabaseQueryTool()
        user_data = await db_tool._arun(user_id)
        
        # 构建推荐提示
        recommendation_prompt = f"""
        基于以下用户数据和需求，生成具体的OOTD推荐：

        用户数据：
        {user_data}

        用户需求：
        {requirements}

        请提供：
        1. 具体的搭配方案（从用户衣橱中选择）
        2. 搭配理由
        3. 适合场合
        4. 风格标签
        5. 置信度评分（0-1）

        请以JSON格式返回推荐结果。
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是专业的时尚顾问，需要基于用户数据生成JSON格式的穿搭推荐。"),
                HumanMessage(content=recommendation_prompt)
            ])
            
            # 解析推荐结果
            recommendation_data = json.loads(response.content)
            
            return OOTDRecommendation(
                outfit_id=f"outfit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                items=recommendation_data.get("items", []),
                occasion=recommendation_data.get("occasion"),
                weather_appropriate=recommendation_data.get("weather_appropriate"),
                style_tags=recommendation_data.get("style_tags", []),
                confidence_score=recommendation_data.get("confidence_score", 0.7),
                reasoning=recommendation_data.get("reasoning", "基于用户数据的个性化推荐")
            )
            
        except Exception as e:
            # 返回默认推荐
            return OOTDRecommendation(
                outfit_id="default_outfit",
                items=[],
                confidence_score=0.5,
                reasoning=f"生成推荐时遇到问题：{str(e)}"
            )

# 创建全局agent实例
_ootd_agent = None

def get_ootd_agent() -> OOTDAgent:
    """获取OOTD agent单例"""
    global _ootd_agent
    if _ootd_agent is None:
        load_dotenv()
        openai_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        _ootd_agent = OOTDAgent(openai_api_key)
    return _ootd_agent