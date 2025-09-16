import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DouyinConfig:
    """抖音小程序配置"""
    APP_ID = os.getenv("DOUYIN_APP_ID", "")
    APP_SECRET = os.getenv("DOUYIN_APP_SECRET", "")
    IS_SANDBOX = os.getenv("DOUYIN_IS_SANDBOX", "0") == "1"
    
    # API域名
    DOMAIN = "developer.toutiao.com"
    SANDBOX_DOMAIN = "open-sandbox.douyin.com"
    
    # API路径
    CODE2SESSION_PATH = "/api/apps/v2/jscode2session"

class Code2SessionResponse(BaseModel):
    """Code2Session响应模型"""
    err_no: int
    err_tips: str
    data: Optional[Dict[str, Any]] = None

class DouyinService:
    """抖音API服务"""
    
    def __init__(self):
        if not DouyinConfig.APP_ID or not DouyinConfig.APP_SECRET:
            logger.warning("抖音小程序配置缺失，请检查环境变量 DOUYIN_APP_ID 和 DOUYIN_APP_SECRET")
    
    async def code2session(self, code: str) -> Dict[str, Any]:
        """
        通过code换取session_key和openid
        
        Args:
            code: 小程序端调用tt.login获取的code
            
        Returns:
            包含openid、session_key、unionid等信息的字典
            
        Raises:
            Exception: 当API调用失败时抛出异常
        """
        if not DouyinConfig.APP_ID or not DouyinConfig.APP_SECRET:
            raise Exception("抖音小程序配置缺失")
        
        # 选择API域名
        domain = DouyinConfig.SANDBOX_DOMAIN if DouyinConfig.IS_SANDBOX else DouyinConfig.DOMAIN
        url = f"https://{domain}{DouyinConfig.CODE2SESSION_PATH}"
        
        # 请求数据
        payload = {
            "appid": DouyinConfig.APP_ID,
            "secret": DouyinConfig.APP_SECRET,
            "code": code,
            "anonymous_code": ""  # 如果需要支持匿名用户可以传入
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP错误: {response.status}")
                    
                    result = await response.json()
                    logger.info(f"Code2Session API响应: {result}")
                    
                    # 解析响应
                    api_response = Code2SessionResponse(**result)
                    
                    if api_response.err_no != 0:
                        raise Exception(f"抖音API错误: {api_response.err_tips}")
                    
                    if not api_response.data:
                        raise Exception("抖音API返回数据为空")
                    
                    # 验证必要字段
                    required_fields = ["openid", "session_key"]
                    for field in required_fields:
                        if field not in api_response.data:
                            raise Exception(f"抖音API返回数据缺失字段: {field}")
                    
                    return api_response.data
                    
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            raise Exception("网络请求失败，请稍后重试")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            raise Exception("API响应格式错误")
        except Exception as e:
            logger.error(f"Code2Session失败: {str(e)}")
            raise

    async def decrypt_data(self, encrypted_data: str, iv: str, session_key: str) -> Dict[str, Any]:
        """
        解密敏感数据（如手机号）
        
        Args:
            encrypted_data: 加密数据
            iv: 初始向量
            session_key: 会话密钥
            
        Returns:
            解密后的数据
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            import base64
            
            # Base64解码
            encrypted_data_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)
            session_key_bytes = base64.b64decode(session_key)
            
            # AES-128-CBC解密
            cipher = Cipher(
                algorithms.AES(session_key_bytes),
                modes.CBC(iv_bytes),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted_bytes = decryptor.update(encrypted_data_bytes) + decryptor.finalize()
            
            # 去除PKCS7填充
            padding_length = decrypted_bytes[-1]
            decrypted_data = decrypted_bytes[:-padding_length]
            
            # 解析JSON
            decrypted_json = json.loads(decrypted_data.decode('utf-8'))
            
            return decrypted_json
            
        except Exception as e:
            logger.error(f"数据解密失败: {str(e)}")
            raise Exception("数据解密失败")

# 创建全局实例
douyin_service = DouyinService()