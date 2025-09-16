class PromptTemplates:
    
    @staticmethod
    def get_style_analysis_prompt(image_count: int = 1) -> str:
        image_instruction = f"这{image_count}张图片" if image_count > 1 else "这张图片"
        
        return f"""
你是一位专业的时尚风格分析师。请分析{image_instruction}中的穿搭风格，并提取关键特征。

分析要求：
1. 服装单品识别：详细描述每件服装的类型、颜色、材质、版型
2. 整体风格定义：判断属于哪种风格流派（韩系/日系/欧美/中式/休闲/正式等）
3. 色彩搭配分析：主色调、配色方案、色彩给人的感受
4. 适合场合：这套搭配适合什么场合和季节
5. 风格关键词：提取3-5个最能代表这个风格的关键词

{"如果有多张图片，请综合分析所有图片的共同风格特征。" if image_count > 1 else ""}

请用以下JSON格式返回，不要包含任何其他文字：
{{
  "clothing_items": [
    {{
      "type": "服装类型",
      "color": "颜色",
      "style": "版型描述",
      "material": "材质推测"
    }}
  ],
  "overall_style": "整体风格名称",
  "style_keywords": ["关键词1", "关键词2", "关键词3"],
  "color_scheme": {{
    "primary_colors": ["主色1", "主色2"],
    "color_mood": "色彩情绪描述"
  }},
  "occasions": ["适合场合1", "适合场合2"],
  "season": "适合季节",
  "style_description": "整体风格的详细文字描述"
}}
"""

    @staticmethod
    def get_user_analysis_prompt(image_count: int = 1) -> str:
        image_instruction = f"这{image_count}张用户照片" if image_count > 1 else "这张用户照片"
        analysis_instruction = "请综合分析所有照片中的用户特征" if image_count > 1 else ""
        
        return f"""
你是一位专业的形象顾问。请分析{image_instruction}，为后续的服装推荐提供个性化建议。

{analysis_instruction}

分析维度：
1. 体型特征：整体身材比例、肩膀宽度、腰臀比例
2. 肤色分析：判断冷调/暖调/中性调，适合的颜色系
3. 脸型识别：脸型特征，适合的服装领型和配饰
4. 个人气质：给人的第一印象和气质类型
5. 风格适配：最适合这个人的3种穿搭风格

{"如果照片中有不同角度或不同类型的照片（如全身照、半身照、脸部特写等），请综合所有信息进行分析。" if image_count > 1 else ""}

请用以下JSON格式返回，不要包含任何其他文字：
{{
  "body_type": {{
    "overall": "整体体型描述",
    "proportions": "身材比例特点", 
    "best_silhouettes": ["适合的版型1", "适合的版型2"]
  }},
  "skin_tone": {{
    "tone_type": "冷调/暖调/中性调",
    "suitable_colors": ["适合颜色1", "适合颜色2", "适合颜色3"],
    "avoid_colors": ["避免颜色1", "避免颜色2"]
  }},
  "face_shape": {{
    "shape": "脸型",
    "suitable_necklines": ["适合领型1", "适合领型2"]
  }},
  "personal_style": {{
    "temperament": "个人气质描述",
    "recommended_styles": ["推荐风格1", "推荐风格2", "推荐风格3"],
    "style_reasons": "推荐理由"
  }}
}}
"""

    @staticmethod
    def get_text_analysis_prompt(user_input: str) -> str:
        return f"""
你是一位贴心的购物助手。请解析用户的文字需求，提取关键信息用于服装推荐。

用户输入：{user_input}

请提取以下信息：
1. 基础信息：身高、体重、年龄、职业等
2. 场合需求：什么场合穿着
3. 风格偏好：喜欢或不喜欢的风格
4. 预算要求：价格范围或消费水平
5. 特殊需求：遮肉、显高、保暖等具体要求
6. 情感表达：用户的情绪和期望

请用以下JSON格式返回，不要包含任何其他文字：
{{
  "basic_info": {{
    "height": "身高(如果提到)",
    "weight": "体重(如果提到)",
    "age_range": "年龄段推测", 
    "occupation": "职业(如果提到)"
  }},
  "occasion": "目标场合",
  "style_preferences": {{
    "liked_styles": ["喜欢的风格"],
    "disliked_styles": ["不喜欢的风格"]
  }},
  "budget": {{
    "range": "预算范围",
    "level": "消费水平(学生/白领/中产/高端)"
  }},
  "special_requirements": ["特殊要求1", "特殊要求2"],
  "emotional_tone": "用户情绪和期望描述",
  "priority": "最重要的需求是什么"
}}
"""