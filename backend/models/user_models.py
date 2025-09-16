from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from models.database_models import ClothingType, Gender, BodyShape, SkinTone
import re

# ===== OpenID认证相关 =====
class OpenIDLogin(BaseModel):
    code: str = Field(..., description="抖音小程序tt.login获取的code")

class OpenIDLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: "UserProfile"
    is_new_user: bool = Field(..., description="是否为新注册用户")

# ===== 用户认证相关（保留向后兼容） =====
class UserRegister(BaseModel):
    phone: str = Field(..., description="手机号")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="用户昵称")
    
    @validator('phone')
    def validate_phone(cls, v):
        # 中国手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v

class UserLogin(BaseModel):
    phone: str = Field(..., description="手机号")
    password: str = Field(..., description="密码")

class UserProfile(BaseModel):
    id: int
    openid: Optional[str] = None  # 脱敏显示的openid
    phone: Optional[str] = None   # 手机号现在是可选的
    nickname: Optional[str] = None
    signature: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[Gender] = None
    height: Optional[int] = None
    weight: Optional[float] = None
    body_shape: Optional[BodyShape] = None
    skin_tone: Optional[SkinTone] = None
    points: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description="用户昵称")
    signature: Optional[str] = Field(None, max_length=200, description="个性签名")
    phone: Optional[str] = Field(None, description="手机号")
    gender: Optional[Gender] = Field(None, description="性别")
    height: Optional[int] = Field(None, ge=100, le=250, description="身高(cm)")
    weight: Optional[float] = Field(None, ge=30, le=200, description="体重(kg)")
    body_shape: Optional[BodyShape] = Field(None, description="体型")
    skin_tone: Optional[SkinTone] = Field(None, description="肤色类型")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            # 中国手机号格式验证
            if not re.match(r'^1[3-9]\d{9}$', v):
                raise ValueError('手机号格式不正确')
        return v

class PasswordChange(BaseModel):
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")

class SetPassword(BaseModel):
    """为OpenID用户设置密码"""
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")

class BindPhone(BaseModel):
    """绑定手机号"""
    phone: str = Field(..., description="手机号")
    
    @validator('phone')
    def validate_phone(cls, v):
        # 中国手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v

# ===== 抖音敏感数据解密相关 =====
class EncryptedData(BaseModel):
    """加密数据"""
    encrypted_data: str = Field(..., description="加密数据")
    iv: str = Field(..., description="初始向量")

class DecryptPhoneRequest(BaseModel):
    """解密手机号请求"""
    encrypted_data: str = Field(..., description="加密的手机号数据")
    iv: str = Field(..., description="初始向量")

# ===== JWT Token相关 =====
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: UserProfile

class TokenData(BaseModel):
    user_id: Optional[int] = None
    openid: Optional[str] = None

# ===== 衣橱相关 =====
class WardrobeCreate(BaseModel):
    type: ClothingType = Field(..., description="服装类型")
    name: str = Field(..., max_length=100, description="服饰名称")
    brand: Optional[str] = Field(None, max_length=50, description="品牌")
    color: str = Field(..., max_length=30, description="颜色")
    size: Optional[str] = Field(None, max_length=20, description="尺码")
    material: Optional[str] = Field(None, max_length=100, description="材质")
    description: Optional[str] = Field(None, description="服饰描述")
    purchase_price: Optional[float] = Field(None, ge=0, description="购买价格")
    purchase_date: Optional[date] = Field(None, description="购买日期")
    purchase_place: Optional[str] = Field(None, max_length=100, description="购买地点")
    season: Optional[str] = Field(None, max_length=20, description="适合季节")
    occasion: Optional[str] = Field(None, max_length=50, description="适合场合")
    style_tags: Optional[List[str]] = Field(None, description="风格标签")

class WardrobeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="服饰名称")
    brand: Optional[str] = Field(None, max_length=50, description="品牌")
    color: Optional[str] = Field(None, max_length=30, description="颜色")
    size: Optional[str] = Field(None, max_length=20, description="尺码")
    material: Optional[str] = Field(None, max_length=100, description="材质")
    description: Optional[str] = Field(None, description="服饰描述")
    purchase_price: Optional[float] = Field(None, ge=0, description="购买价格")
    purchase_date: Optional[date] = Field(None, description="购买日期")
    purchase_place: Optional[str] = Field(None, max_length=100, description="购买地点")
    season: Optional[str] = Field(None, max_length=20, description="适合季节")
    occasion: Optional[str] = Field(None, max_length=50, description="适合场合")
    style_tags: Optional[List[str]] = Field(None, description="风格标签")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    is_available: Optional[bool] = Field(None, description="是否可用")

class WardrobeResponse(BaseModel):
    id: int
    user_id: int
    type: ClothingType
    name: str
    brand: Optional[str] = None
    color: str
    size: Optional[str] = None
    material: Optional[str] = None
    image_url: str
    description: Optional[str] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    purchase_place: Optional[str] = None
    wear_count: int = 0
    last_worn_date: Optional[date] = None
    season: Optional[str] = None
    occasion: Optional[str] = None
    style_tags: List[str] = []
    is_favorite: bool = False
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WardrobeFilter(BaseModel):
    type: Optional[ClothingType] = Field(None, description="服装类型")
    brand: Optional[str] = Field(None, description="品牌")
    color: Optional[str] = Field(None, description="颜色")
    season: Optional[str] = Field(None, description="季节")
    occasion: Optional[str] = Field(None, description="场合")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    is_available: Optional[bool] = Field(None, description="是否可用")

class WardrobeStatistics(BaseModel):
    total_items: int
    items_by_type: dict
    favorite_count: int
    most_worn_item: Optional[WardrobeResponse] = None
    least_worn_items: List[WardrobeResponse] = []
    total_value: float

# ===== 通用响应模型 =====
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class PaginatedResponse(BaseModel):
    success: bool
    message: str
    data: List[dict]
    total: int
    page: int
    size: int
    has_next: bool

# ===== 用户会话相关 =====
class SessionCreate(BaseModel):
    session_id: str
    style_analysis_data: Optional[dict] = None
    user_analysis_data: Optional[dict] = None
    text_analysis_data: Optional[dict] = None

class SessionUpdate(BaseModel):
    style_analysis_data: Optional[dict] = None
    user_analysis_data: Optional[dict] = None
    text_analysis_data: Optional[dict] = None
    final_recommendation_data: Optional[dict] = None
    personalized_response: Optional[str] = None
    avatar_url: Optional[str] = None
    confidence_score: Optional[float] = None
    is_completed: Optional[bool] = None

class SessionResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    session_id: str
    is_completed: bool
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# 解决循环引用问题
OpenIDLoginResponse.update_forward_refs()