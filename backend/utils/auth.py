from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from models.database_models import User
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30天

# 安全方案
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user_by_phone(phone: str, password: str) -> Optional[User]:
    """通过手机号和密码验证用户 - 保留原有方法"""
    user = await User.get_or_none(phone=phone, is_active=True)
    if not user or not user.verify_password(password):
        return None
    return user

async def authenticate_user_by_openid(openid: str) -> Optional[User]:
    """通过OpenID验证用户"""
    user = await User.get_or_none(openid=openid, is_active=True)
    return user

async def get_or_create_user_by_openid(openid: str, **user_data) -> User:
    """根据OpenID获取或创建用户"""
    user = await User.get_or_none(openid=openid)
    
    if not user:
        # 创建新用户
        user = await User.create_user_by_openid(openid, **user_data)
        logger.info(f"新用户通过OpenID创建: {openid[:8]}****")
    else:
        # 更新用户最后活跃时间
        user.updated_at = datetime.utcnow()
        await user.save()
        logger.info(f"用户通过OpenID登录: {openid[:8]}****")
    
    return user

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """从JWT令牌获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 支持两种令牌格式：基于user_id和基于openid
        user_id: Optional[int] = payload.get("sub")  # 传统格式
        openid: Optional[str] = payload.get("openid")  # 新格式
        
        if user_id:
            # 传统的基于user_id的令牌
            user = await User.get_or_none(id=int(user_id), is_active=True)
        elif openid:
            # 基于openid的令牌
            user = await User.get_or_none(openid=openid, is_active=True)
        else:
            raise credentials_exception
            
        if user is None:
            raise credentials_exception
            
        return user
        
    except JWTError as e:
        logger.error(f"JWT解析失败: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"获取用户失败: {str(e)}")
        raise credentials_exception

# 为了向后兼容，保留原有的函数名
authenticate_user = authenticate_user_by_phone
get_current_active_user = get_current_user_from_token

# 新增的便捷函数
async def create_token_for_user(user: User) -> str:
    """为用户创建JWT令牌"""
    token_data = {
        "sub": str(user.id),
        "openid": user.openid,
        "user_id": user.id
    }
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(data=token_data, expires_delta=access_token_expires)

def verify_token(token: str) -> Optional[dict]:
    """验证JWT令牌并返回载荷"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None