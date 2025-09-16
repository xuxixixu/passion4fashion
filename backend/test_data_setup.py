# test_data_setup.py - 用于插入测试数据的脚本
import asyncio
import os
from datetime import date
from tortoise import Tortoise
from models.database_models import User, Wardrobe, ClothingType, Gender, BodyShape, SkinTone

# 数据库配置 - 根据你的实际配置调整
DATABASE_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "12345678",  # 修改为你的数据库密码
                "database": "fashion",        # 修改为你的数据库名
            }
        }
    },
    "apps": {
        "models": {
            "models": ["models.database_models"],
            "default_connection": "default",
        }
    }
}

async def create_test_user():
    """创建测试用户"""
    print("创建测试用户...")
    
    # 检查用户是否已存在
    existing_user = await User.get_or_none(id=1)
    if existing_user:
        print("测试用户已存在，跳过创建")
        return existing_user
    
    # 创建新的测试用户
    user = await User.create_user_by_openid(
        openid="test_openid_12345",
        nickname="时尚测试用户",
        phone="13800138000",
        gender=Gender.FEMALE,
        height=165,
        weight=55.0,
        body_shape=BodyShape.HOURGLASS,
        skin_tone=SkinTone.WARM,
        signature="喜欢简约优雅的穿搭风格"
    )
    
    print(f"创建测试用户成功: ID={user.id}, 昵称={user.nickname}")
    return user

async def create_test_wardrobe_items(user):
    """为测试用户创建衣橱数据"""
    print("创建测试衣橱数据...")
    
    # 检查是否已有衣橱数据
    existing_items = await Wardrobe.filter(user=user)
    if existing_items:
        print(f"测试用户已有 {len(existing_items)} 件衣物，跳过创建")
        return existing_items
    
    # 测试衣物数据
    wardrobe_items = [
        # 上衣
        {
            "type": ClothingType.TOP,
            "name": "白色衬衫",
            "brand": "ZARA",
            "color": "白色",
            "size": "M",
            "material": "棉质",
            "season": "春夏秋",
            "occasion": "商务,休闲",
            "style_tags": "简约,经典,百搭",
            "purchase_price": 199.00,
            "purchase_date": date(2024, 3, 15),
            "wear_count": 15,
            "is_favorite": True
        },
        {
            "type": ClothingType.TOP,
            "name": "黑色针织衫",
            "brand": "优衣库",
            "color": "黑色",
            "size": "M",
            "material": "羊毛混纺",
            "season": "秋冬",
            "occasion": "休闲,约会",
            "style_tags": "温暖,舒适,简约",
            "purchase_price": 299.00,
            "purchase_date": date(2024, 10, 20),
            "wear_count": 8,
            "is_favorite": True
        },
        {
            "type": ClothingType.TOP,
            "name": "条纹T恤",
            "brand": "H&M",
            "color": "蓝白条纹",
            "size": "M",
            "material": "棉质",
            "season": "春夏",
            "occasion": "休闲,运动",
            "style_tags": "休闲,青春,舒适",
            "purchase_price": 79.00,
            "purchase_date": date(2024, 5, 10),
            "wear_count": 22,
            "is_favorite": False
        },
        
        # 下装
        {
            "type": ClothingType.BOTTOM,
            "name": "黑色西装裤",
            "brand": "ZARA",
            "color": "黑色",
            "size": "M",
            "material": "聚酯纤维",
            "season": "四季",
            "occasion": "商务,正式",
            "style_tags": "正式,修身,专业",
            "purchase_price": 299.00,
            "purchase_date": date(2024, 2, 28),
            "wear_count": 12,
            "is_favorite": True
        },
        {
            "type": ClothingType.BOTTOM,
            "name": "牛仔裤",
            "brand": "Levi's",
            "color": "深蓝色",
            "size": "M",
            "material": "棉质牛仔布",
            "season": "春夏秋",
            "occasion": "休闲,约会",
            "style_tags": "休闲,经典,百搭",
            "purchase_price": 599.00,
            "purchase_date": date(2024, 1, 15),
            "wear_count": 35,
            "is_favorite": True
        },
        {
            "type": ClothingType.BOTTOM,
            "name": "米色阔腿裤",
            "brand": "COS",
            "color": "米色",
            "size": "M",
            "material": "亚麻混纺",
            "season": "春夏",
            "occasion": "休闲,度假",
            "style_tags": "慵懒,优雅,舒适",
            "purchase_price": 399.00,
            "purchase_date": date(2024, 4, 8),
            "wear_count": 6,
            "is_favorite": False
        },
        
        # 连衣裙
        {
            "type": ClothingType.DRESS,
            "name": "小黑裙",
            "brand": "ZARA",
            "color": "黑色",
            "size": "M",
            "material": "聚酯纤维",
            "season": "四季",
            "occasion": "正式,约会,聚会",
            "style_tags": "经典,优雅,性感",
            "purchase_price": 399.00,
            "purchase_date": date(2024, 6, 20),
            "wear_count": 5,
            "is_favorite": True
        },
        {
            "type": ClothingType.DRESS,
            "name": "碎花连衣裙",
            "brand": "MANGO",
            "color": "粉色碎花",
            "size": "M",
            "material": "雪纺",
            "season": "春夏",
            "occasion": "休闲,约会,度假",
            "style_tags": "甜美,浪漫,飘逸",
            "purchase_price": 299.00,
            "purchase_date": date(2024, 7, 12),
            "wear_count": 3,
            "is_favorite": False
        },
        
        # 外套
        {
            "type": ClothingType.OUTERWEAR,
            "name": "风衣",
            "brand": "Burberry",
            "color": "卡其色",
            "size": "M",
            "material": "棉质防水布",
            "season": "春秋",
            "occasion": "商务,休闲,正式",
            "style_tags": "经典,优雅,专业",
            "purchase_price": 1299.00,
            "purchase_date": date(2024, 9, 5),
            "wear_count": 4,
            "is_favorite": True
        },
        {
            "type": ClothingType.OUTERWEAR,
            "name": "羽绒服",
            "brand": "优衣库",
            "color": "深蓝色",
            "size": "M",
            "material": "尼龙+羽绒",
            "season": "冬季",
            "occasion": "休闲,运动",
            "style_tags": "保暖,轻便,运动",
            "purchase_price": 599.00,
            "purchase_date": date(2024, 11, 18),
            "wear_count": 2,
            "is_favorite": False
        },
        
        # 鞋履
        {
            "type": ClothingType.SHOES,
            "name": "黑色高跟鞋",
            "brand": "Jimmy Choo",
            "color": "黑色",
            "size": "38",
            "material": "真皮",
            "season": "四季",
            "occasion": "正式,商务,聚会",
            "style_tags": "优雅,正式,性感",
            "purchase_price": 899.00,
            "purchase_date": date(2024, 3, 28),
            "wear_count": 8,
            "is_favorite": True
        },
        {
            "type": ClothingType.SHOES,
            "name": "白色运动鞋",
            "brand": "Adidas",
            "color": "白色",
            "size": "38",
            "material": "皮革+橡胶",
            "season": "春夏秋",
            "occasion": "休闲,运动",
            "style_tags": "运动,舒适,百搭",
            "purchase_price": 599.00,
            "purchase_date": date(2024, 4, 15),
            "wear_count": 25,
            "is_favorite": True
        },
        {
            "type": ClothingType.SHOES,
            "name": "棕色乐福鞋",
            "brand": "Gucci",
            "color": "棕色",
            "size": "38",
            "material": "真皮",
            "season": "春夏秋",
            "occasion": "商务,休闲",
            "style_tags": "经典,舒适,精致",
            "purchase_price": 1199.00,
            "purchase_date": date(2024, 8, 10),
            "wear_count": 6,
            "is_favorite": False
        },
        
        # 包包
        {
            "type": ClothingType.BAG,
            "name": "黑色手提包",
            "brand": "LV",
            "color": "黑色",
            "material": "真皮",
            "season": "四季",
            "occasion": "商务,正式,聚会",
            "style_tags": "奢华,经典,精致",
            "purchase_price": 2999.00,
            "purchase_date": date(2024, 5, 25),
            "wear_count": 10,
            "is_favorite": True
        },
        {
            "type": ClothingType.BAG,
            "name": "帆布双肩包",
            "brand": "Fjällräven",
            "color": "军绿色",
            "material": "帆布",
            "season": "四季",
            "occasion": "休闲,旅行,学习",
            "style_tags": "休闲,实用,环保",
            "purchase_price": 599.00,
            "purchase_date": date(2024, 7, 8),
            "wear_count": 18,
            "is_favorite": False
        }
    ]
    
    created_items = []
    for item_data in wardrobe_items:
        # 生成一个模拟的图片URL
        item_data["image_url"] = f"https://example.com/images/{item_data['name'].replace(' ', '_')}.jpg"
        item_data["description"] = f"这是一件{item_data['color']}的{item_data['name']}，来自{item_data['brand']}品牌。"
        
        # 创建衣物项目
        wardrobe_item = await Wardrobe.create(
            user=user,
            **item_data
        )
        created_items.append(wardrobe_item)
        print(f"创建衣物: {wardrobe_item.name} ({wardrobe_item.type})")
    
    print(f"成功创建 {len(created_items)} 件测试衣物")
    return created_items

async def main():
    """主函数"""
    print("开始设置OOTD测试数据...")
    
    try:
        # 初始化数据库连接
        await Tortoise.init(config=DATABASE_CONFIG)
        print("数据库连接成功")
        
        # 创建测试用户
        user = await create_test_user()
        
        # 创建测试衣橱数据
        wardrobe_items = await create_test_wardrobe_items(user)
        
        print("\n" + "="*50)
        print("测试数据设置完成！")
        print(f"用户ID: {user.id}")
        print(f"用户昵称: {user.nickname}")
        print(f"衣橱物品数量: {len(wardrobe_items)}")
        print("="*50)
        print("\n现在您可以：")
        print("1. 启动FastAPI应用")
        print("2. 在前端测试页面中输入用户ID: 1")
        print("3. 通过 /api/users/login 获取访问令牌")
        print("4. 开始与OOTD助手对话！")
        
    except Exception as e:
        print(f"设置测试数据时发生错误: {str(e)}")
        raise
    finally:
        # 关闭数据库连接
        await Tortoise.close_connections()

if __name__ == "__main__":
    # 检查环境
    if not os.path.exists("models"):
        print("错误: 请在项目根目录下运行此脚本")
        exit(1)
    
    # 运行测试数据设置
    asyncio.run(main())