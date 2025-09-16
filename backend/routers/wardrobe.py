import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from tortoise.queryset import Q
from models.database_models import User, Wardrobe, ClothingType
from models.user_models import (
    WardrobeCreate, WardrobeUpdate, WardrobeResponse, 
    WardrobeFilter, WardrobeStatistics, StandardResponse, PaginatedResponse
)
from utils.auth import get_current_active_user
from datetime import date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wardrobe", tags=["衣橱管理"])

@router.post("/items", response_model=StandardResponse)
async def create_wardrobe_item(
    item_data: WardrobeCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    添加衣橱物品
    注意：image_url字段将在上传图片后更新，前端需要通过 /api/wardrobe/images/{user_id}/{filename} 来获取实际图片
    """
    try:
        # 处理风格标签
        style_tags_str = ",".join(item_data.style_tags) if item_data.style_tags else None
        
        # 创建衣橱物品（先不包含图片）
        wardrobe_item = await Wardrobe.create(
            user=current_user,
            type=item_data.type,
            name=item_data.name,
            brand=item_data.brand,
            color=item_data.color,
            size=item_data.size,
            material=item_data.material,
            image_url="",  # 临时空值，后续更新
            description=item_data.description,
            purchase_price=item_data.purchase_price,
            purchase_date=item_data.purchase_date,
            purchase_place=item_data.purchase_place,
            season=item_data.season,
            occasion=item_data.occasion,
            style_tags=style_tags_str
        )
        
        logger.info(f"用户 {current_user.phone} 添加衣橱物品: {item_data.name}")
        
        return StandardResponse(
            success=True,
            message="衣橱物品添加成功",
            data={
                "item_id": wardrobe_item.id,
                "note": "请上传物品图片完成创建"
            }
        )
        
    except Exception as e:
        logger.error(f"添加衣橱物品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加失败，请稍后重试"
        )

@router.post("/items/{item_id}/upload-image", response_model=StandardResponse)
async def upload_wardrobe_image(
    item_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    为衣橱物品上传图片
    返回的image_url是文件名，前端需要通过 /api/wardrobe/images/{user_id}/{filename} 来获取实际图片
    """
    try:
        # 验证物品归属
        wardrobe_item = await Wardrobe.get_or_none(id=item_id, user=current_user)
        if not wardrobe_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="衣橱物品不存在"
            )
        
        # 验证文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持图片文件"
            )
        
        # 验证文件大小 (例如限制为10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件大小不能超过10MB"
            )
        
        # 创建用户衣橱图片目录
        wardrobe_dir = f"user_data/{current_user.id}/wardrobe"
        os.makedirs(wardrobe_dir, exist_ok=True)
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        image_filename = f"wardrobe_{item_id}_{uuid.uuid4()}{file_extension}"
        image_path = os.path.join(wardrobe_dir, image_filename)
        
        # 删除旧图片文件（如果存在）
        if wardrobe_item.image_url:
            old_image_path = os.path.join(wardrobe_dir, wardrobe_item.image_url)
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except Exception as e:
                    logger.warning(f"删除旧衣橱图片失败: {str(e)}")
        
        # 保存新文件
        with open(image_path, "wb") as buffer:
            buffer.write(file_content)
        
        # 更新衣橱物品图片URL（存储文件名）
        wardrobe_item.image_url = image_filename
        await wardrobe_item.save()
        
        logger.info(f"衣橱物品图片上传成功: {wardrobe_item.name}, 文件名: {image_filename}")
        
        return StandardResponse(
            success=True,
            message="图片上传成功",
            data={
                "image_url": image_filename,
                "message": f"前端请通过 /api/wardrobe/images/{current_user.id}/{image_filename} 来获取图片"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"衣橱图片上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="图片上传失败，请稍后重试"
        )

@router.get("/images/{user_id}/{filename}")
async def get_wardrobe_image(user_id: int, filename: str):
    """
    获取衣橱图片文件
    这个端点用于提供实际的图片文件，前端在显示衣橱图片时应该调用这个接口
    
    安全性说明：
    - 理想情况下应该通过认证验证访问权限
    - 当前版本为了保持现有API兼容性，暂时保持user_id参数
    - 建议在生产环境中添加访问权限控制
    """
    try:
        # 验证用户ID（基本的输入验证）
        if user_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的用户ID"
            )
        
        # 验证文件名格式（防止路径遍历攻击）
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名"
            )
        
        # 验证文件扩展名安全性
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件格式"
            )
        
        image_path = os.path.join(f"user_data/{user_id}/wardrobe", filename)
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片文件不存在"
            )
        
        # 额外安全检查：确保文件路径在预期目录内
        abs_image_path = os.path.abspath(image_path)
        expected_dir = os.path.abspath(f"user_data/{user_id}/wardrobe")
        if not abs_image_path.startswith(expected_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="访问被拒绝"
            )
        
        # 返回文件，设置适当的缓存头
        return FileResponse(
            image_path,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "Content-Type": f"image/{file_extension[1:]}",
                "X-Content-Type-Options": "nosniff"  # 防止MIME类型嗅探攻击
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取衣橱图片失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取图片失败"
        )

@router.get("/items", response_model=PaginatedResponse)
async def get_wardrobe_items(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[ClothingType] = Query(None, description="服装类型"),
    brand: Optional[str] = Query(None, description="品牌"),
    color: Optional[str] = Query(None, description="颜色"),
    season: Optional[str] = Query(None, description="季节"),
    occasion: Optional[str] = Query(None, description="场合"),
    is_favorite: Optional[bool] = Query(None, description="是否收藏"),
    is_available: Optional[bool] = Query(None, description="是否可用"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户衣橱物品列表（支持分页和筛选）
    注意：返回的image_url字段是文件名，前端需要构建完整URL来获取图片
    """
    try:
        # 构建查询条件
        query = Wardrobe.filter(user=current_user)
        
        if type:
            query = query.filter(type=type)
        if brand:
            query = query.filter(brand__icontains=brand)
        if color:
            query = query.filter(color__icontains=color)
        if season:
            query = query.filter(season__icontains=season)
        if occasion:
            query = query.filter(occasion__icontains=occasion)
        if is_favorite is not None:
            query = query.filter(is_favorite=is_favorite)
        if is_available is not None:
            query = query.filter(is_available=is_available)
        
        # 获取总数
        total = await query.count()
        
        # 分页查询
        offset = (page - 1) * size
        items = await query.offset(offset).limit(size).order_by('-created_at')
        
        # 转换为响应格式
        items_data = [item.to_dict() for item in items]
        
        return PaginatedResponse(
            success=True,
            message="获取衣橱物品成功",
            data=items_data,
            total=total,
            page=page,
            size=size,
            has_next=total > page * size
        )
        
    except Exception as e:
        logger.error(f"获取衣橱物品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取衣橱物品失败"
        )

@router.get("/items/{item_id}", response_model=WardrobeResponse)
async def get_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取单个衣橱物品详情
    注意：返回的image_url字段是文件名，前端需要构建完整URL来获取图片
    """
    try:
        wardrobe_item = await Wardrobe.get_or_none(id=item_id, user=current_user)
        if not wardrobe_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="衣橱物品不存在"
            )
        
        return WardrobeResponse(**wardrobe_item.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取衣橱物品详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取物品详情失败"
        )

@router.put("/items/{item_id}", response_model=StandardResponse)
async def update_wardrobe_item(
    item_id: int,
    item_data: WardrobeUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    更新衣橱物品
    """
    try:
        wardrobe_item = await Wardrobe.get_or_none(id=item_id, user=current_user)
        if not wardrobe_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="衣橱物品不存在"
            )
        
        # 只更新提供的字段
        update_data = item_data.dict(exclude_unset=True)
        
        # 处理风格标签
        if 'style_tags' in update_data and update_data['style_tags']:
            update_data['style_tags'] = ",".join(update_data['style_tags'])
        
        for field, value in update_data.items():
            setattr(wardrobe_item, field, value)
        
        await wardrobe_item.save()
        
        logger.info(f"衣橱物品更新成功: {wardrobe_item.name}")
        
        return StandardResponse(
            success=True,
            message="衣橱物品更新成功",
            data=wardrobe_item.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新衣橱物品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败，请稍后重试"
        )

@router.delete("/items/{item_id}", response_model=StandardResponse)
async def delete_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    删除衣橱物品
    """
    try:
        wardrobe_item = await Wardrobe.get_or_none(id=item_id, user=current_user)
        if not wardrobe_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="衣橱物品不存在"
            )
        
        # 删除相关图片文件
        if wardrobe_item.image_url:
            try:
                # 构建图片文件的完整路径
                image_path = os.path.join(f"user_data/{current_user.id}/wardrobe", wardrobe_item.image_url)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"已删除衣橱图片文件: {image_path}")
            except Exception as e:
                logger.warning(f"删除衣橱图片文件失败: {str(e)}")
        
        item_name = wardrobe_item.name
        await wardrobe_item.delete()
        
        logger.info(f"衣橱物品删除成功: {item_name}")
        
        return StandardResponse(
            success=True,
            message="衣橱物品删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除衣橱物品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败，请稍后重试"
        )

@router.post("/items/{item_id}/wear", response_model=StandardResponse)
async def record_wear(
    item_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    记录穿戴次数
    """
    try:
        wardrobe_item = await Wardrobe.get_or_none(id=item_id, user=current_user)
        if not wardrobe_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="衣橱物品不存在"
            )
        
        await wardrobe_item.add_wear_count()
        
        return StandardResponse(
            success=True,
            message="穿戴记录成功",
            data={
                "wear_count": wardrobe_item.wear_count,
                "last_worn_date": wardrobe_item.last_worn_date.isoformat() if wardrobe_item.last_worn_date else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录穿戴失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="记录穿戴失败"
        )

@router.get("/statistics", response_model=WardrobeStatistics)
async def get_wardrobe_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取衣橱统计信息
    注意：返回的图片URL字段是文件名，前端需要构建完整URL来获取图片
    """
    try:
        # 获取所有衣橱物品
        all_items = await Wardrobe.filter(user=current_user, is_available=True)
        
        if not all_items:
            return WardrobeStatistics(
                total_items=0,
                items_by_type={},
                favorite_count=0,
                total_value=0.0
            )
        
        # 统计各类型数量
        items_by_type = {}
        for item in all_items:
            if item.type in items_by_type:
                items_by_type[item.type] += 1
            else:
                items_by_type[item.type] = 1
        
        # 统计收藏数量
        favorite_count = len([item for item in all_items if item.is_favorite])
        
        # 找出最常穿和最少穿的物品
        most_worn_item = max(all_items, key=lambda x: x.wear_count) if all_items else None
        least_worn_items = sorted(all_items, key=lambda x: x.wear_count)[:5]
        
        # 计算总价值
        total_value = sum(float(item.purchase_price or 0) for item in all_items)
        
        return WardrobeStatistics(
            total_items=len(all_items),
            items_by_type=items_by_type,
            favorite_count=favorite_count,
            most_worn_item=WardrobeResponse(**most_worn_item.to_dict()) if most_worn_item else None,
            least_worn_items=[WardrobeResponse(**item.to_dict()) for item in least_worn_items],
            total_value=total_value
        )
        
    except Exception as e:
        logger.error(f"获取衣橱统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "wardrobe-management"}