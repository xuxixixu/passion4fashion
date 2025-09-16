# models/extended_models.py
from tortoise.models import Model
from tortoise import fields
from enum import Enum
from datetime import datetime, timezone

class Platform(str, Enum):
    """平台类型枚举"""
    DOUYIN = "抖音"
    XIAOHONGSHU = "小红书"
    WEIBO = "微博"
    BILIBILI = "B站"
    OTHER = "其他"

class ProductCategory(str, Enum):
    """商品类别枚举"""
    CLOTHING = "服装"
    SHOES = "鞋履"
    BAGS = "包袋"
    ACCESSORIES = "配饰"
    COSMETICS = "美妆"
    SKINCARE = "护肤"
    FRAGRANCE = "香水"

class Product(Model):
    """商品信息表"""
    id = fields.IntField(pk=True, description="商品ID")
    
    # 基本信息
    name = fields.CharField(max_length=200, description="商品名称")
    brand = fields.CharField(max_length=100, null=True, description="品牌")
    category = fields.CharEnumField(ProductCategory, description="商品类别")
    subcategory = fields.CharField(max_length=100, null=True, description="子类别")
    
    # 价格信息
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="价格")
    original_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="原价")
    currency = fields.CharField(max_length=10, default="CNY", description="货币单位")
    
    # 详细信息
    description = fields.TextField(null=True, description="商品描述")
    features = fields.TextField(null=True, description="商品特点")
    materials = fields.CharField(max_length=500, null=True, description="材质")
    colors = fields.JSONField(null=True, description="可选颜色")
    sizes = fields.JSONField(null=True, description="可选尺码")
    
    # 图片信息 - 存储相对路径
    main_image = fields.CharField(max_length=500, null=True, description="主图相对路径")
    detail_images = fields.JSONField(null=True, description="详情图相对路径数组")
    
    # 风格和标签
    style_tags = fields.JSONField(null=True, description="风格标签")
    occasion_tags = fields.JSONField(null=True, description="场合标签")
    season_tags = fields.JSONField(null=True, description="季节标签")
    
    # 适用人群
    suitable_age_range = fields.CharField(max_length=50, null=True, description="适合年龄段")
    suitable_body_types = fields.JSONField(null=True, description="适合体型")
    suitable_skin_tones = fields.JSONField(null=True, description="适合肤色")
    
    # 购买信息
    purchase_url = fields.CharField(max_length=1000, null=True, description="购买链接")
    platform = fields.CharField(max_length=100, null=True, description="销售平台")
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否有效")
    stock_status = fields.CharField(max_length=50, default="in_stock", description="库存状态")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "products"
        table_description = "商品信息表"
    
    def __str__(self):
        return f"Product({self.name}, {self.brand})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "subcategory": self.subcategory,
            "price": float(self.price) if self.price else None,
            "original_price": float(self.original_price) if self.original_price else None,
            "currency": self.currency,
            "description": self.description,
            "features": self.features,
            "materials": self.materials,
            "colors": self.colors,
            "sizes": self.sizes,
            "main_image": self.main_image,
            "detail_images": self.detail_images,
            "style_tags": self.style_tags,
            "occasion_tags": self.occasion_tags,
            "season_tags": self.season_tags,
            "suitable_age_range": self.suitable_age_range,
            "suitable_body_types": self.suitable_body_types,
            "suitable_skin_tones": self.suitable_skin_tones,
            "purchase_url": self.purchase_url,
            "platform": self.platform,
            "is_active": self.is_active,
            "stock_status": self.stock_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Influencer(Model):
    """博主信息表"""
    id = fields.IntField(pk=True, description="博主ID")
    
    # 基本信息
    name = fields.CharField(max_length=100, description="博主名称")
    platform = fields.CharEnumField(Platform, description="主要平台")
    platform_id = fields.CharField(max_length=200, null=True, description="平台账号ID")
    avatar = fields.CharField(max_length=500, null=True, description="头像相对路径")
    
    # 个人信息
    bio = fields.TextField(null=True, description="个人简介")
    age_range = fields.CharField(max_length=20, null=True, description="年龄段")
    height = fields.IntField(null=True, description="身高(cm)")
    body_type = fields.CharField(max_length=50, null=True, description="体型")
    skin_tone = fields.CharField(max_length=50, null=True, description="肤色")
    
    # 风格特征
    style_tags = fields.JSONField(null=True, description="风格标签")
    primary_styles = fields.JSONField(null=True, description="主要风格")
    content_types = fields.JSONField(null=True, description="内容类型")
    
    # 专业领域
    expertise_areas = fields.JSONField(null=True, description="专业领域")
    price_range = fields.CharField(max_length=100, null=True, description="推荐价格区间")
    
    # 受众特征
    target_audience = fields.JSONField(null=True, description="目标受众")
    suitable_body_types = fields.JSONField(null=True, description="适合体型")
    suitable_age_ranges = fields.JSONField(null=True, description="适合年龄段")
    
    # 社交数据
    followers_count = fields.IntField(null=True, description="粉丝数")
    engagement_rate = fields.FloatField(null=True, description="互动率")
    
    # 联系信息
    contact_info = fields.JSONField(null=True, description="联系方式")
    collaboration_rates = fields.JSONField(null=True, description="合作报价")
    
    # 作品示例
    featured_posts = fields.JSONField(null=True, description="精选作品")
    portfolio_images = fields.JSONField(null=True, description="作品集图片路径")
    
    # 状态
    is_active = fields.BooleanField(default=True, description="是否有效")
    verification_status = fields.CharField(max_length=50, default="pending", description="认证状态")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "influencers"
        table_description = "博主信息表"
    
    def __str__(self):
        return f"Influencer({self.name}, {self.platform})"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "platform_id": self.platform_id,
            "avatar": self.avatar,
            "bio": self.bio,
            "age_range": self.age_range,
            "height": self.height,
            "body_type": self.body_type,
            "skin_tone": self.skin_tone,
            "style_tags": self.style_tags,
            "primary_styles": self.primary_styles,
            "content_types": self.content_types,
            "expertise_areas": self.expertise_areas,
            "price_range": self.price_range,
            "target_audience": self.target_audience,
            "suitable_body_types": self.suitable_body_types,
            "suitable_age_ranges": self.suitable_age_ranges,
            "followers_count": self.followers_count,
            "engagement_rate": self.engagement_rate,
            "contact_info": self.contact_info,
            "collaboration_rates": self.collaboration_rates,
            "featured_posts": self.featured_posts,
            "portfolio_images": self.portfolio_images,
            "is_active": self.is_active,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class DataChangeLog(Model):
    """数据变更日志表 - 用于向量数据库同步"""
    id = fields.IntField(pk=True, description="日志ID")
    table_name = fields.CharField(max_length=50, description="表名")
    record_id = fields.IntField(description="记录ID")
    operation = fields.CharField(max_length=10, description="操作类型: INSERT/UPDATE/DELETE")
    processed = fields.BooleanField(default=False, description="是否已处理")
    processed_at = fields.DatetimeField(null=True, description="处理时间")
    error_message = fields.TextField(null=True, description="错误信息")
    retry_count = fields.IntField(default=0, description="重试次数")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    
    class Meta:
        table = "data_change_log"
        table_description = "数据变更日志表"
    
    def __str__(self):
        return f"DataChangeLog({self.table_name}, {self.record_id}, {self.operation})"