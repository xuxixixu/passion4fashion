from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class StyleType(str, Enum):
    KOREAN = "韩系"
    JAPANESE = "日系"
    EUROPEAN = "欧美"
    CHINESE = "中式"
    CASUAL = "休闲"
    FORMAL = "正式"
    VINTAGE = "复古"
    MINIMALIST = "极简"
    BOHEMIAN = "波西米亚"

class SeasonType(str, Enum):
    SPRING = "春季"
    SUMMER = "夏季"
    AUTUMN = "秋季"
    WINTER = "冬季"
    ALL_SEASON = "四季"

class OccasionType(str, Enum):
    DAILY = "日常"
    WORK = "工作"
    DATE = "约会"
    PARTY = "聚会"
    FORMAL = "正式场合"
    TRAVEL = "旅行"
    SPORTS = "运动"

# ===== 风格图片分析结果 =====
class ClothingItem(BaseModel):
    type: str = Field(description="服装类型")
    color: str = Field(description="颜色")
    style: str = Field(description="版型描述")
    material: str = Field(description="材质推测")

class ColorScheme(BaseModel):
    primary_colors: List[str] = Field(description="主色调列表")
    color_mood: str = Field(description="色彩情绪描述")

class StyleAnalysisResult(BaseModel):
    clothing_items: List[ClothingItem] = Field(description="服装单品列表")
    overall_style: str = Field(description="整体风格名称")
    style_keywords: List[str] = Field(description="风格关键词")
    color_scheme: ColorScheme = Field(description="色彩搭配方案")
    occasions: List[str] = Field(description="适合场合")
    season: str = Field(description="适合季节")
    style_description: str = Field(description="整体风格详细描述")
    confidence_score: Optional[float] = Field(default=None, description="分析置信度")

# ===== 用户照片分析结果 =====
class BodyType(BaseModel):
    overall: str = Field(description="整体体型描述")
    proportions: str = Field(description="身材比例特点")
    best_silhouettes: List[str] = Field(description="适合的版型")

class SkinTone(BaseModel):
    tone_type: str = Field(description="肤色类型：冷调/暖调/中性调")
    suitable_colors: List[str] = Field(description="适合的颜色")
    avoid_colors: List[str] = Field(description="应避免的颜色")

class FaceShape(BaseModel):
    shape: str = Field(description="脸型")
    suitable_necklines: List[str] = Field(description="适合的领型")

class PersonalStyle(BaseModel):
    temperament: str = Field(description="个人气质描述")
    recommended_styles: List[str] = Field(description="推荐风格")
    style_reasons: str = Field(description="推荐理由")

class UserAnalysisResult(BaseModel):
    body_type: BodyType = Field(description="体型特征")
    skin_tone: SkinTone = Field(description="肤色分析")
    face_shape: FaceShape = Field(description="脸型分析")
    personal_style: PersonalStyle = Field(description="个人风格")
    confidence_score: Optional[float] = Field(default=None, description="分析置信度")

# ===== 文字需求解析结果 =====
class BasicInfo(BaseModel):
    height: Optional[str] = Field(default=None, description="身高")
    weight: Optional[str] = Field(default=None, description="体重")
    age_range: Optional[str] = Field(default=None, description="年龄段")
    occupation: Optional[str] = Field(default=None, description="职业")

class StylePreferences(BaseModel):
    liked_styles: List[str] = Field(default=[], description="喜欢的风格")
    disliked_styles: List[str] = Field(default=[], description="不喜欢的风格")

class Budget(BaseModel):
    range: Optional[str] = Field(default=None, description="预算范围")
    level: Optional[str] = Field(default=None, description="消费水平")

class TextAnalysisResult(BaseModel):
    basic_info: BasicInfo = Field(description="基础信息")
    occasion: Optional[str] = Field(default=None, description="目标场合")
    style_preferences: StylePreferences = Field(description="风格偏好")
    budget: Budget = Field(description="预算信息")
    special_requirements: List[str] = Field(default=[], description="特殊要求")
    emotional_tone: Optional[str] = Field(default=None, description="情感基调")
    priority: Optional[str] = Field(default=None, description="优先级需求")
    confidence_score: Optional[float] = Field(default=None, description="解析置信度")

# ===== 综合推荐结果 =====
class CompatibilityAnalysis(BaseModel):
    match_score: float = Field(description="匹配度评分(1-10)")
    strengths: List[str] = Field(description="用户条件优势")
    adjustments: List[str] = Field(description="需要调整的地方")

class RecommendedItem(BaseModel):
    category: str = Field(description="单品类别")
    description: str = Field(description="具体描述")
    color: str = Field(description="颜色")
    style: str = Field(description="款式")
    why_suitable: str = Field(description="选择理由")
    priority: Optional[int] = Field(default=None, description="推荐优先级")

class OutfitRecommendation(BaseModel):
    theme: str = Field(description="方案主题")
    items: List[RecommendedItem] = Field(description="单品列表")
    overall_effect: str = Field(description="整体效果描述")
    acceptance_prediction: str = Field(description="用户接受度预测")
    styling_tips: List[str] = Field(default=[], description="搭配技巧")

class FinalRecommendationResult(BaseModel):
    compatibility_analysis: CompatibilityAnalysis = Field(description="兼容性分析")
    outfit_recommendations: List[OutfitRecommendation] = Field(description="搭配推荐方案")
    shopping_priority: List[str] = Field(description="购物优先级")
    styling_tips: List[str] = Field(description="搭配小贴士")
    confidence_boost: str = Field(description="自信提升说明")
    overall_confidence: Optional[float] = Field(default=None, description="整体推荐置信度")

# ===== 完整分析结果（包含所有分析维度） =====
class ComprehensiveAnalysisResult(BaseModel):
    style_analysis: Optional[StyleAnalysisResult] = Field(default=None, description="风格图片分析")
    user_analysis: Optional[UserAnalysisResult] = Field(default=None, description="用户照片分析")
    text_analysis: Optional[TextAnalysisResult] = Field(default=None, description="文字需求分析")
    final_recommendation: Optional[FinalRecommendationResult] = Field(default=None, description="最终推荐结果")
    analysis_timestamp: Optional[str] = Field(default=None, description="分析时间戳")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    
    class Config:
        arbitrary_types_allowed = True