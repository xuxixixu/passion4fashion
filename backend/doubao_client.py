import httpx
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, AsyncIterator
from pydantic import BaseModel
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class MessageContentType(str, Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"
    VIDEO_URL = "video_url"

class MessageContent(BaseModel):
    type: MessageContentType
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None
    video_url: Optional[Dict[str, str]] = None

class ChatMessage(BaseModel):
    role: MessageRole
    content: Union[str, List[MessageContent]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None

class ChatCompletionStreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None

class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]

class DoubaoError(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

class DoubaoClient:
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        self.api_key = api_key or os.getenv("DOUBAO_API_KEY")
        self.base_url = base_url or os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("API key is required. Set DOUBAO_API_KEY environment variable or pass api_key parameter.")
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def close(self):
        await self.client.aclose()

    def _prepare_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        prepared_messages = []
        for msg in messages:
            if isinstance(msg.content, str):
                prepared_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            elif isinstance(msg.content, list):
                content_list = []
                for content_item in msg.content:
                    if content_item.type == MessageContentType.TEXT:
                        content_list.append({
                            "type": "text",
                            "text": content_item.text
                        })
                    elif content_item.type == MessageContentType.IMAGE_URL:
                        content_list.append({
                            "type": "image_url",
                            "image_url": content_item.image_url
                        })
                    elif content_item.type == MessageContentType.VIDEO_URL:
                        content_list.append({
                            "type": "video_url",
                            "video_url": content_item.video_url
                        })
                prepared_messages.append({
                    "role": msg.role.value,
                    "content": content_list
                })
        return prepared_messages

    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.post(url, json=data)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise DoubaoError("Rate limit exceeded", response.status_code)
                else:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f": {error_detail}"
                    except:
                        error_msg += f": {response.text}"
                    raise DoubaoError(error_msg, response.status_code)
                    
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise DoubaoError("Request timeout")
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise DoubaoError(str(e))

    async def create_chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = False,
        top_p: Optional[float] = 1.0,
    ) -> Union[ChatCompletionResponse, AsyncIterator[ChatCompletionStreamResponse]]:
        
        request_data = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if max_tokens:
            request_data["max_tokens"] = max_tokens
            
        if stream:
            request_data["stream"] = True
            return self._stream_chat_completion(request_data)
        else:
            response_data = await self._make_request("chat/completions", request_data)
            return ChatCompletionResponse(**response_data)

    async def _stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncIterator[ChatCompletionStreamResponse]:
        url = f"{self.base_url}/chat/completions"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            client.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
            
            async with client.stream("POST", url, json=request_data) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise DoubaoError(f"Stream request failed: {error_text}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            yield ChatCompletionStreamResponse(**data)
                        except json.JSONDecodeError:
                            continue

    async def simple_chat(
        self,
        model: str,
        user_message: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        messages = []
        if system_message:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_message))
        messages.append(ChatMessage(role=MessageRole.USER, content=user_message))
        
        response = await self.create_chat_completion(
            model=model,
            messages=messages,
            **kwargs
        )
        
        if isinstance(response, ChatCompletionResponse):
            return response.choices[0].message.content
        else:
            full_response = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.get("content"):
                    full_response += chunk.choices[0].delta["content"]
            return full_response

    @staticmethod
    def create_text_content(text: str) -> MessageContent:
        return MessageContent(type=MessageContentType.TEXT, text=text)

    @staticmethod
    def create_image_content(image_url: str, detail: str = "auto") -> MessageContent:
        return MessageContent(
            type=MessageContentType.IMAGE_URL,
            image_url={"url": image_url, "detail": detail}
        )

    @staticmethod
    def create_video_content(video_url: str) -> MessageContent:
        return MessageContent(
            type=MessageContentType.VIDEO_URL,
            video_url={"url": video_url}
        )

    async def create_image_generation(
        self,
        model: str,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        quality: str = "high",
        style: str = "vivid",
        response_format: str = "url"
    ) -> Dict[str, Any]:
        """
        调用豆包图像生成API
        
        Args:
            model: 图像生成模型名称
            prompt: 图像描述文本
            size: 图像尺寸，如 "1024x1024", "1024x1792", "1792x1024"
            n: 生成图片数量，默认为1
            quality: 图片质量，可选 "standard" 或 "high"
            style: 图片风格，可选 "vivid" 或 "natural"
            response_format: 返回格式，可选 "url" 或 "b64_json"
            
        Returns:
            Dict: 包含生成的图片信息
        """
        
        request_data = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": response_format
        }
        
        try:
            # 使用图像生成端点
            response_data = await self._make_request("images/generations", request_data)
            return response_data
            
        except DoubaoError as e:
            # 如果图像生成端点不存在，尝试使用聊天端点作为后备
            logger.warning(f"图像生成端点不可用，尝试聊天端点: {e}")
            
            # 后备方案：使用聊天端点生成描述
            fallback_messages = [
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"请生成一张图片：{prompt}"
                )
            ]
            
            fallback_response = await self.create_chat_completion(
                model=model,
                messages=fallback_messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            # 返回格式化的响应
            return {
                "data": [{
                    "url": f"data:text/plain,{fallback_response.choices[0].message.content}",
                    "revised_prompt": prompt
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "note": "使用后备方案，实际未生成图像"
            }