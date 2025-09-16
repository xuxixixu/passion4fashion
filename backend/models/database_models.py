from tortoise.models import Model
from tortoise import fields
from enum import Enum
from typing import Optional
import bcrypt
import secrets
from datetime import datetime, timezone

class ClothingType(str, Enum):
    """服装类型枚举"""
    TOP = "上衣"
    BOTTOM = "下装" 
    DRESS = "连衣裙"
    OUTERWEAR = "外套"
    SHOES = "鞋履"
    BAG = "背包"
    ACCESSORY = "配饰"

class Gender(str, Enum):
    """性别枚举"""
    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"

class BodyShape(str, Enum):
    """体型枚举"""
    PEAR = "梨形"
    APPLE = "苹果形"
    HOURGLASS = "沙漏形"
    RECTANGLE = "矩形"
    INVERTED_TRIANGLE = "倒三角形"
    OVAL = "椭圆形"

class SkinTone(str, Enum):
    """肤色类型枚举"""
    COOL = "冷调"
    WARM = "暖调"
    NEUTRAL = "中性调"

class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image" 
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"

class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class User(Model):
    """用户信息表"""
    id = fields.IntField(pk=True, description="用户ID")
    openid = fields.CharField(max_length=128, unique=True, description="抖音OpenID")
    phone = fields.CharField(max_length=20, unique=True, null=True, description="手机号")
    password_hash = fields.CharField(max_length=255, null=True, description="密码哈希")
    nickname = fields.CharField(max_length=50, null=True, description="用户昵称")
    signature = fields.CharField(max_length=200, null=True, description="个性签名")
    avatar_url = fields.CharField(max_length=500, null=True, description="头像URL")
    
    # 身材相关信息
    gender = fields.CharEnumField(Gender, null=True, description="性别")
    height = fields.IntField(null=True, description="身高(cm)")
    weight = fields.FloatField(null=True, description="体重(kg)")
    body_shape = fields.CharEnumField(BodyShape, null=True, description="体型")
    skin_tone = fields.CharEnumField(SkinTone, null=True, description="肤色类型")
    
    # 系统信息
    points = fields.IntField(default=0, description="积分")
    latest_session_id = fields.CharField(max_length=100, null=True, description="最新会话ID")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    is_active = fields.BooleanField(default=True, description="是否激活")
    
    class Meta:
        table = "users"
        table_description = "用户信息表"
    
    def __str__(self):
        return f"User({self.openid}, {self.nickname})"
    
    @classmethod
    async def create_user_by_openid(cls, openid: str, **kwargs):
        """通过OpenID创建新用户"""
        user = await cls.create(
            openid=openid,
            **kwargs
        )
        return user
    
    @classmethod
    async def create_user(cls, phone: str, password: str, **kwargs):
        """创建新用户 - 保留原有方法兼容性"""
        # 生成密码哈希
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = await cls.create(
            phone=phone,
            password_hash=password_hash,
            **kwargs
        )
        return user
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    async def update_password(self, new_password: str):
        """更新密码"""
        self.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        await self.save()
    
    def to_dict(self):
        """转换为字典，排除敏感信息"""
        return {
            "id": self.id,
            "openid": self.openid[:8] + "****" if self.openid else None,  # 脱敏显示
            "phone": self.phone,
            "nickname": self.nickname,
            "signature": self.signature,
            "avatar_url": self.avatar_url,
            "gender": self.gender,
            "height": self.height,
            "weight": self.weight,
            "body_shape": self.body_shape,
            "skin_tone": self.skin_tone,
            "points": self.points,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Wardrobe(Model):
    """衣橱表"""
    id = fields.IntField(pk=True, description="服饰ID")
    user = fields.ForeignKeyField("models.User", related_name="wardrobe_items", description="所属用户")
    
    # 基本信息
    type = fields.CharEnumField(ClothingType, description="服装类型")
    name = fields.CharField(max_length=100, description="服饰名称")
    brand = fields.CharField(max_length=50, null=True, description="品牌")
    color = fields.CharField(max_length=30, description="颜色")
    size = fields.CharField(max_length=20, null=True, description="尺码")
    material = fields.CharField(max_length=100, null=True, description="材质")
    
    # 图片和描述
    image_url = fields.CharField(max_length=500, description="服饰图片URL")
    description = fields.TextField(null=True, description="服饰描述")
    
    # 购买信息
    purchase_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="购买价格")
    purchase_date = fields.DateField(null=True, description="购买日期")
    purchase_place = fields.CharField(max_length=100, null=True, description="购买地点")
    
    # 使用情况
    wear_count = fields.IntField(default=0, description="穿戴次数")
    last_worn_date = fields.DateField(null=True, description="最后穿戴日期")
    
    # 分类标签
    season = fields.CharField(max_length=20, null=True, description="适合季节")
    occasion = fields.CharField(max_length=50, null=True, description="适合场合")
    style_tags = fields.CharField(max_length=200, null=True, description="风格标签，逗号分隔")
    
    # 状态
    is_favorite = fields.BooleanField(default=False, description="是否收藏")
    is_available = fields.BooleanField(default=True, description="是否可用（未损坏、未丢失等）")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="添加时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "wardrobe"
        table_description = "衣橱表"
    
    def __str__(self):
        return f"Wardrobe({self.name}, {self.type}, User: {self.user_id})"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "name": self.name,
            "brand": self.brand,
            "color": self.color,
            "size": self.size,
            "material": self.material,
            "image_url": self.image_url,
            "description": self.description,
            "purchase_price": float(self.purchase_price) if self.purchase_price else None,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_place": self.purchase_place,
            "wear_count": self.wear_count,
            "last_worn_date": self.last_worn_date.isoformat() if self.last_worn_date else None,
            "season": self.season,
            "occasion": self.occasion,
            "style_tags": self.style_tags.split(",") if self.style_tags else [],
            "is_favorite": self.is_favorite,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    async def add_wear_count(self):
        """增加穿戴次数"""
        self.wear_count += 1
        self.last_worn_date = fields.DateField().to_python_value(None)  # 当前日期
        await self.save()

class UserSession(Model):
    """用户会话表"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="sessions", null=True, description="关联用户")
    session_id = fields.CharField(max_length=100, unique=True, description="会话ID")
    
    # 分析数据
    style_analysis_data = fields.JSONField(null=True, description="风格分析数据")
    user_analysis_data = fields.JSONField(null=True, description="用户分析数据")
    text_analysis_data = fields.JSONField(null=True, description="文本分析数据")
    final_recommendation_data = fields.JSONField(null=True, description="最终推荐数据")
    
    # 生成的内容
    personalized_response = fields.TextField(null=True, description="个性化回复")
    avatar_url = fields.CharField(max_length=500, null=True, description="生成的头像URL")
    
    # 状态和统计
    is_completed = fields.BooleanField(default=False, description="是否完成分析")
    confidence_score = fields.FloatField(null=True, description="分析置信度")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "user_sessions"
        table_description = "用户会话表"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "is_completed": self.is_completed,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ConversationMessage(Model):
    """OOTD对话记录表"""
    id = fields.IntField(pk=True, description="消息ID")
    user = fields.ForeignKeyField("models.User", related_name="ootd_conversations", description="所属用户")
    
    # 消息基本信息
    message_id = fields.CharField(max_length=100, description="唯一消息标识符")
    role = fields.CharEnumField(MessageRole, description="消息角色")
    content_type = fields.CharEnumField(MessageType, description="内容类型")
    
    # 消息内容
    text_content = fields.TextField(null=True, description="文本内容")
    file_path = fields.CharField(max_length=500, null=True, description="文件存储路径")
    metadata = fields.JSONField(null=True, description="元数据(文件大小、原始文件名等)")
    
    # 对话会话信息
    conversation_id = fields.CharField(max_length=100, description="对话会话ID")
    sequence_number = fields.IntField(description="消息在对话中的序号")
    
    # 时间信息
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    
    # 处理状态
    is_processed = fields.BooleanField(default=False, description="是否已处理")
    processing_result = fields.JSONField(null=True, description="处理结果")
    
    class Meta:
        table = "ootd_conversation_messages"
        table_description = "OOTD对话记录表"
        ordering = ["conversation_id", "sequence_number"]
    
    def __str__(self):
        return f"Message({self.conversation_id}, {self.role}, {self.sequence_number})"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "role": self.role,
            "content_type": self.content_type,
            "text_content": self.text_content,
            "file_path": self.file_path,
            "metadata": self.metadata,
            "conversation_id": self.conversation_id,
            "sequence_number": self.sequence_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_processed": self.is_processed,
            "processing_result": self.processing_result
        }
    
    @classmethod
    async def get_conversation_history(cls, user_id: int, conversation_id: str, limit: int = 50):
        """获取对话历史"""
        messages = await cls.filter(
            user_id=user_id,
            conversation_id=conversation_id
        ).order_by("sequence_number").limit(limit)
        return messages
    
    @classmethod
    async def get_recent_messages(cls, user_id: int, hours: int = 2):
        """获取最近几小时内的消息"""
        from datetime import datetime, timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        messages = await cls.filter(
            user_id=user_id,
            created_at__gte=cutoff_time
        ).order_by("-created_at").limit(100)
        return messages

class OOTDSession(Model):
    """OOTD对话会话表"""
    id = fields.IntField(pk=True, description="会话ID")
    user = fields.ForeignKeyField("models.User", related_name="ootd_sessions", description="所属用户")
    
    # 会话基本信息
    session_id = fields.CharField(max_length=100, unique=True, description="会话标识符")
    title = fields.CharField(max_length=200, null=True, description="会话标题")
    
    # 会话状态
    is_active = fields.BooleanField(default=True, description="是否活跃")
    message_count = fields.IntField(default=0, description="消息数量")
    
    # 上下文信息
    user_preferences = fields.JSONField(null=True, description="用户偏好设置")
    session_context = fields.JSONField(null=True, description="会话上下文")
    
    # 时间信息
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    last_message_at = fields.DatetimeField(null=True, description="最后消息时间")
    
    class Meta:
        table = "ootd_sessions"
        table_description = "OOTD对话会话表"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "title": self.title,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "user_preferences": self.user_preferences,
            "session_context": self.session_context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }
    
    async def add_message_count(self):
        """增加消息计数"""
        self.message_count += 1
        self.last_message_at = datetime.now(timezone.utc)
        await self.save()