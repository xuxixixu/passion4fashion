import os
import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import FileResponse
from tortoise.exceptions import IntegrityError
from models.database_models import User, UserSession
from models.user_models import (
    UserRegister, UserLogin, UserProfile, UserUpdate, 
    PasswordChange, Token, StandardResponse
)
from utils.auth import (
    create_access_token, authenticate_user_by_phone, get_current_user_from_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# ===== 保留原有的手机号+密码认证方式（向后兼容） =====

@router.post("/register", response_model=StandardResponse)
async def register(user_data: UserRegister):
    """
    传统手机号密码注册（保留兼容性）
    注意：现在推荐使用OpenID认证方式
    """
    try:
        # 检查用户是否已存在
        existing_user = await User.get_or_none(phone=user_data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )
        
        # 创建新用户 - 注意：没有openid的用户
        user = await User.create_user(
            phone=user_data.phone,
            password=user_data.password,
            nickname=user_data.nickname,
            openid=f"legacy_{uuid.uuid4().hex[:16]}"  # 为兼容性生成假openid
        )
        
        logger.info(f"传统方式新用户注册成功: {user.phone}")
        
        return StandardResponse(
            success=True,
            message="注册成功",
            data={"user_id": user.id}
        )
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号已被注册"
        )
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """
    传统手机号密码登录（保留兼容性）
    """
    try:
        # 验证用户
        user = await authenticate_user_by_phone(user_data.phone, user_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "openid": user.openid}, expires_delta=access_token_expires
        )
        
        logger.info(f"传统方式用户登录成功: {user.phone}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info=UserProfile(**user.to_dict())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

# ===== 用户信息管理（兼容OpenID和传统认证） =====

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user_from_token)):
    """
    获取当前用户信息
    注意：avatar_url字段返回的是文件名，前端需要通过 /api/users/avatars/{filename} 来获取实际图片
    """
    return UserProfile(**current_user.to_dict())

@router.put("/profile", response_model=StandardResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    更新用户信息
    """
    try:
        # 只更新提供的字段
        update_data = user_data.dict(exclude_unset=True)
        
        # 特殊处理手机号更新 - 检查是否被其他用户使用
        if "phone" in update_data and update_data["phone"]:
            existing_phone_user = await User.get_or_none(phone=update_data["phone"])
            if existing_phone_user and existing_phone_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该手机号已被其他用户使用"
                )
        
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        await current_user.save()
        
        logger.info(f"用户信息更新成功: {current_user.openid[:8] if current_user.openid else current_user.phone}****")
        
        return StandardResponse(
            success=True,
            message="信息更新成功",
            data=current_user.to_dict()
        )
        
    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被其他用户使用"
        )
    except Exception as e:
        logger.error(f"用户信息更新失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败，请稍后重试"
        )

@router.post("/change-password", response_model=StandardResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    修改密码
    """
    try:
        # 验证原密码
        if not current_user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前用户未设置密码，请使用设置密码功能"
            )
            
        if not current_user.verify_password(password_data.old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原密码错误"
            )
        
        # 更新密码
        await current_user.update_password(password_data.new_password)
        
        logger.info(f"用户密码修改成功: {current_user.openid[:8] if current_user.openid else current_user.phone}****")
        
        return StandardResponse(
            success=True,
            message="密码修改成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码修改失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败，请稍后重试"
        )

@router.post("/upload-avatar", response_model=StandardResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    上传用户头像
    返回的avatar_url是文件名，前端需要通过 /api/users/avatars/{filename} 来获取实际图片
    """
    try:
        # 验证文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持图片文件"
            )
        
        # 验证文件大小 (例如限制为5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件大小不能超过5MB"
            )
        
        # 创建用户头像目录
        avatar_dir = f"user_data/avatars"
        os.makedirs(avatar_dir, exist_ok=True)
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        avatar_filename = f"avatar_{current_user.id}_{uuid.uuid4()}{file_extension}"
        avatar_path = os.path.join(avatar_dir, avatar_filename)
        
        # 删除旧头像文件（如果存在）
        if current_user.avatar_url:
            old_avatar_path = os.path.join(avatar_dir, current_user.avatar_url)
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                except Exception as e:
                    logger.warning(f"删除旧头像失败: {str(e)}")
        
        # 保存新文件
        with open(avatar_path, "wb") as buffer:
            buffer.write(file_content)
        
        # 更新用户头像URL（存储文件名）
        current_user.avatar_url = avatar_filename
        await current_user.save()
        
        logger.info(f"用户头像上传成功: {current_user.openid[:8] if current_user.openid else current_user.phone}****, 文件名: {avatar_filename}")
        
        return StandardResponse(
            success=True,
            message="头像上传成功",
            data={
                "avatar_url": avatar_filename,
                "message": "前端请通过 /api/users/avatars/{filename} 来获取图片"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="头像上传失败，请稍后重试"
        )

@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """
    获取用户头像文件
    这个端点用于提供实际的图片文件，前端在显示头像时应该调用这个接口
    """
    try:
        avatar_path = os.path.join("user_data/avatars", filename)
        
        # 检查文件是否存在
        if not os.path.exists(avatar_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="头像文件不存在"
            )
        
        # 验证文件扩展名安全性
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件格式"
            )
        
        # 验证文件名格式（防止路径遍历攻击）
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名"
            )
        
        # 返回文件，设置适当的缓存头
        return FileResponse(
            avatar_path,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "Content-Type": f"image/{file_extension[1:]}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取头像文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取头像失败"
        )

@router.post("/update-session", response_model=StandardResponse)
async def update_latest_session(
    session_id: str,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    更新用户最新会话ID
    """
    try:
        current_user.latest_session_id = session_id
        await current_user.save()
        
        return StandardResponse(
            success=True,
            message="会话ID更新成功"
        )
        
    except Exception as e:
        logger.error(f"更新会话ID失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败，请稍后重试"
        )

@router.post("/add-points", response_model=StandardResponse)
async def add_points(
    points: int,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    增加用户积分（管理员功能或任务奖励）
    """
    try:
        if points <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="积分必须大于0"
            )
        
        current_user.points += points
        await current_user.save()
        
        logger.info(f"用户积分增加: {current_user.openid[:8] if current_user.openid else current_user.phone}****, +{points}")
        
        return StandardResponse(
            success=True,
            message=f"积分增加成功，+{points}",
            data={"total_points": current_user.points}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"积分增加失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="积分增加失败，请稍后重试"
        )

@router.delete("/account", response_model=StandardResponse)
async def delete_account(
    current_user: User = Depends(get_current_user_from_token)
):
    """
    删除用户账户（软删除）
    """
    try:
        current_user.is_active = False
        await current_user.save()
        
        logger.info(f"用户账户删除: {current_user.openid[:8] if current_user.openid else current_user.phone}****")
        
        return StandardResponse(
            success=True,
            message="账户删除成功"
        )
        
    except Exception as e:
        logger.error(f"账户删除失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="账户删除失败，请稍后重试"
        )

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "user-management"}