# agents/enhanced_ootd_agent.py
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
from models.extended_models import Product, Influencer
from services.vector_db_service import get_vector_service
from dotenv import load_dotenv

class DatabaseQueryTool(BaseTool):
    """数据库查询工具"""
    name: str = "database_query"
    description: str = "查询用户的个人信息和衣橱数据，用于生成个性化OOTD建议"
    
    def _run(self, user_id: int) -> str:
        return self._arun(user_id)
    
    async def _arun(self, user_id: int) -> str:
        try:
            user = await User.get_or_none(id=user_id)
            if not user:
                return "用户不存在"
            
            wardrobe_items = await Wardrobe.filter(user_id=user_id, is_available=True)
            
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
            
            for item in wardrobe_items:
                item_type = item.type
                if item_type not in user_data["wardrobe"]["items_by_type"]:
                    user_data["wardrobe"]["items_by_type"][item_type] = 0
                user_data["wardrobe"]["items_by_type"][item_type] += 1
                
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

class ProductSearchTool(BaseTool):
    """商品搜索工具"""
    name: str = "product_search"
    description: str = "根据用户需求搜索相关商品，可以基于风格、场合、类型等进行搜索"
    
    def _run(self, query: str, limit: int = 5) -> str:
        return self._arun(query, limit)
    
    async def _arun(self, query: str, limit: int = 5) -> str:
        try:
            vector_service = get_vector_service()
            search_results = await vector_service.search_products(query, limit)
            
            if not search_results:
                return "未找到相关商品"
            
            formatted_results = []
            for result in search_results:
                product_info = {
                    "id": result["id"],
                    "similarity": 1 - result["distance"],  # 转换为相似度
                    "metadata": result["metadata"]
                }
                formatted_results.append(product_info)
            
            return json.dumps({
                "query": query,
                "found_products": len(formatted_results),
                "products": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"搜索商品时发生错误：{str(e)}"

class InfluencerRecommendTool(BaseTool):
    """博主推荐工具"""
    name: str = "influencer_recommend"
    description: str = "根据用户特征和风格偏好推荐合适的时尚博主"
    
    def _run(self, query: str, limit: int = 3) -> str:
        return self._arun(query, limit)
    
    async def _arun(self, query: str, limit: int = 3) -> str:
        try:
            vector_service = get_vector_service()
            search_results = await vector_service.search_influencers(query, limit)
            
            if not search_results:
                return "未找到合适的博主推荐"
            
            formatted_results = []
            for result in search_results:
                influencer_info = {
                    "id": result["id"],
                    "similarity": 1 - result["distance"],
                    "metadata": result["metadata"]
                }
                formatted_results.append(influencer_info)
            
            return json.dumps({
                "query": query,
                "found_influencers": len(formatted_results),
                "influencers": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"推荐博主时发生错误：{str(e)}"

class ConversationHistoryTool(BaseTool):
    """对话历史查询工具"""
    name: str = "conversation_history"
    description: str = "获取用户最近的对话历史，了解用户的偏好和上下文"
    
    def _run(self, user_id: int, hours: int = 2) -> str:
        return self._arun(user_id, hours)
    
    async def _arun(self, user_id: int, hours: int = 2) -> str:
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

class EnhancedOOTDAgent:
    """增强版OOTD智能助手 - 支持商品推荐和博主推荐"""
    
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
            ProductSearchTool(),
            InfluencerRecommendTool(),
        ]
        
        # 注意：prompt和agent将在chat方法中动态创建以支持页面上下文
        pass
    
    def _get_system_prompt(self, page_context: str = None) -> str:
        """获取系统提示"""
        base_prompt = """你是一个专业的OOTD时尚助手，现在拥有了更强大的能力：

1. **理解用户需求**：
   - 仔细分析用户的穿搭需求和场景
   - 如果用户的问题不够具体，主动询问详细信息（场合、天气、心情、风格偏好等）

2. **个性化分析**：
   - 使用database_query工具获取用户的身材数据和衣橱信息
   - 根据用户的体型、肤色、已有衣物进行分析
   - 考虑用户的历史偏好和穿搭习惯

3. **商品推荐**：
   - 使用product_search工具搜索适合的商品
   - 基于用户需求、场合、风格等搜索相关商品
   - 结合用户现有衣橱，推荐互补的单品
   - 考虑性价比和实用性

4. **博主推荐**：
   - 使用influencer_recommend工具推荐合适的博主
   - 基于用户的体型、风格偏好匹配相似博主
   - 推荐适合用户参考的穿搭博主和内容创作者

5. **专业建议**：
   - 提供具体的搭配建议，包括颜色、款式、配饰等
   - 解释推荐理由，包括为什么这样搭配适合用户
   - 考虑实用性：天气、场合、舒适度等因素
   - 如果推荐商品，说明选择理由和搭配方法
   - 如果推荐博主，说明为什么适合用户参考

6. **工具使用策略**：
   - 个性化建议时：先调用database_query获取用户数据
   - 需要购买建议时：调用product_search搜索合适商品
   - 需要参考inspiration时：调用influencer_recommend推荐博主
   - 需要了解偏好时：调用conversation_history查看历史
   - 通用时尚咨询：无需调用工具，直接提供专业建议

7. **响应格式**：
   - 保持友好、专业的语气"""
        
        # 根据页面上下文添加特定提示
        context_prompts = {
            "home": "\n\n**当前场景：首页**\n你是用户的全能时尚助手！欢迎用户来到OOTD平台，介绍平台的主要功能：AI风格分析、智能衣橱管理、个性化穿搭推荐等。主动询问用户想要什么帮助，引导用户探索不同功能页面。",
            "style_analysis": "\n\n**当前场景：AI风格分析页**\n专注于用户的风格分析和个性化建议！引导用户尝试风格分析功能，提供细致的个人风格诊断，推荐适合的穿搭风格和色彩搭配。强调AI分析的专业性和个性化。",
            "wardrobe": "\n\n**当前场景：衣橱页**\n专注于衣橱管理和穿搭推荐！根据用户现有的衣物进行OOTD推荐，提供单品搭配建议，推荐互补商品。帮助用户充分利用现有衣橱，创造更多穿搭可能。",
            "profile": "\n\n**当前场景：个人页面**\n专注于个人信息完善和量身定制！邀请用户填写或更新详细的个人信息（身材数据、风格偏好、生活场景等），强调完善信息对获得精准推荐的重要性，提供个性化的服务建议。"
        }
        
        if page_context and page_context in context_prompts:
            return base_prompt + context_prompts[page_context]
        
        return base_prompt
    """   - 结构化回答：现有搭配分析 + 推荐方案 + 购买建议 + 博主参考
    - 提供具体可操作的建议
    - 鼓励用户反馈，持续优化建议

    记住，你的目标是成为用户的全方位时尚顾问，不仅帮助搭配现有衣物，还能推荐新品和参考博主，让用户在任何场合都自信美丽！"""

    async def chat(self, user_id: int, message: str, chat_history: List[BaseMessage] = None, page_context: str = None) -> Dict[str, Any]:
        """处理用户消息"""
        if chat_history is None:
            chat_history = []
        
        # 根据页面上下文动态创建prompt和agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt(page_context)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True
        )
        
        try:
            result = await executor.ainvoke({
                "input": message,
                "chat_history": chat_history,
                "user_id": user_id
            })
            
            # 分析使用了哪些工具
            tools_used = []
            user_data_used = False
            products_recommended = False
            influencers_recommended = False
            
            for step in result.get("intermediate_steps", []):
                if "database_query" in str(step):
                    tools_used.append("user_data")
                    user_data_used = True
                if "product_search" in str(step):
                    tools_used.append("product_search")
                    products_recommended = True
                if "influencer_recommend" in str(step):
                    tools_used.append("influencer_recommend")
                    influencers_recommended = True
                if "conversation_history" in str(step):
                    tools_used.append("conversation_history")
            
            return {
                "response": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "tools_used": tools_used,
                "user_data_used": user_data_used,
                "products_recommended": products_recommended,
                "influencers_recommended": influencers_recommended
            }
            
        except Exception as e:
            return {
                "response": f"抱歉，处理您的请求时遇到了问题：{str(e)}",
                "intermediate_steps": [],
                "tools_used": [],
                "user_data_used": False,
                "products_recommended": False,
                "influencers_recommended": False
            }

# 创建全局agent实例
_enhanced_ootd_agent = None

def get_enhanced_ootd_agent() -> EnhancedOOTDAgent:
    """获取增强版OOTD agent单例"""
    global _enhanced_ootd_agent
    if _enhanced_ootd_agent is None:
        load_dotenv()
        openai_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        _enhanced_ootd_agent = EnhancedOOTDAgent(openai_api_key)
    return _enhanced_ootd_agent