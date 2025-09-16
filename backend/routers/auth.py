from fastapi import APIRouter, HTTPException, Depends, status
from models.database_models import User
from models.user_models import (
    OpenIDLogin, OpenIDLoginResponse, UserProfile, StandardResponse,
    BindPhone, SetPassword, DecryptPhoneRequest
)
from services.douyin_service import douyin_service
from utils.auth import (
    get_current_user_from_token, create_token_for_user,
    get_or_create_user_by_openid, ACCESS_TOKEN_EXPIRE_MINUTES
)
from tortoise.exceptions import IntegrityError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["OpenID认证"])

@router.post("/openid-login", response_model=OpenIDLoginResponse)
async def openid_login(login_data: OpenIDLogin):
    """
    使用抖音OpenID登录/注册
    用户进入小程序后，自动通过code换取openid，实现静默登录
    """
    try:
        # 通过抖音API获取用户信息
        douyin_data = await douyin_service.code2session(login_data.code)
        openid = douyin_data.get("openid")
        
        if not openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法获取用户标识"
            )
        
        # 检查是否为新用户
        existing_user = await User.get_or_none(openid=openid)
        is_new_user = existing_user is None
        
        # 获取或创建用户
        user = await get_or_create_user_by_openid(
            openid=openid,
            nickname=f"用户{openid[-6:]}"  # 使用openid后6位作为默认昵称
        )
        
        # 生成JWT令牌
        access_token = await create_token_for_user(user)
        
        logger.info(f"OpenID登录{'（新用户）' if is_new_user else ''}成功: {openid[:8]}****")
        
        return OpenIDLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info=UserProfile(**user.to_dict()),
            is_new_user=is_new_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenID登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

@router.post("/bind-phone", response_model=StandardResponse)
async def bind_phone(
    phone_data: BindPhone,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    为OpenID用户绑定手机号
    """
    try:
        # 检查手机号是否已被其他用户使用
        existing_phone_user = await User.get_or_none(phone=phone_data.phone)
        if existing_phone_user and existing_phone_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被其他用户使用"
            )
        
        # 绑定手机号
        current_user.phone = phone_data.phone
        await current_user.save()
        
        logger.info(f"用户 {current_user.openid[:8]}**** 绑定手机号成功: {phone_data.phone}")
        
        return StandardResponse(
            success=True,
            message="手机号绑定成功",
            data={"phone": phone_data.phone}
        )
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被其他用户使用"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"绑定手机号失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="绑定失败，请稍后重试"
        )

@router.post("/set-password", response_model=StandardResponse)
async def set_password(
    password_data: SetPassword,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    为OpenID用户设置密码
    """
    try:
        # 设置密码
        await current_user.update_password(password_data.new_password)
        
        logger.info(f"用户 {current_user.openid[:8]}**** 设置密码成功")
        
        return StandardResponse(
            success=True,
            message="密码设置成功"
        )
        
    except Exception as e:
        logger.error(f"设置密码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置密码失败，请稍后重试"
        )

@router.post("/decrypt-phone", response_model=StandardResponse)
async def decrypt_phone(
    decrypt_data: DecryptPhoneRequest,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    解密用户手机号并自动绑定
    当用户在小程序中授权获取手机号时调用此接口
    """
    try:
        # 从数据库或缓存中获取session_key
        # 注意：这里需要你实现session_key的存储机制
        # 可以考虑在UserSession表中存储，或使用Redis等缓存
        
        # 临时方案：从抖音API重新获取（不推荐在生产环境使用）
        # 在实际应用中，应该在登录时存储session_key，这里直接使用
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="手机号解密功能需要实现session_key存储机制"
        )
        
        # 解密手机号的代码示例（需要实现session_key存储后启用）
        """
        session_key = "从存储中获取用户的session_key"
        
        decrypted_data = await douyin_service.decrypt_data(
            decrypt_data.encrypted_data,
            decrypt_data.iv,
            session_key
        )
        
        phone_number = decrypted_data.get("phoneNumber")
        if phone_number:
            # 检查手机号是否已被使用
            existing_user = await User.get_or_none(phone=phone_number)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该手机号已被其他用户使用"
                )
            
            # 绑定手机号
            current_user.phone = phone_number
            await current_user.save()
            
            return StandardResponse(
                success=True,
                message="手机号获取并绑定成功",
                data={"phone": phone_number}
            )
        """
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解密手机号失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取手机号失败，请稍后重试"
        )

@router.get("/current-user", response_model=UserProfile)
async def get_current_user(current_user: User = Depends(get_current_user_from_token)):
    """
    获取当前用户信息
    """
    return UserProfile(**current_user.to_dict())

@router.post("/logout", response_model=StandardResponse)
async def logout(current_user: User = Depends(get_current_user_from_token)):
    """
    用户登出
    注意：JWT令牌是无状态的，实际的登出需要在客户端清除token
    这个接口主要用于记录日志和清理服务端资源
    """
    try:
        logger.info(f"用户登出: {current_user.openid[:8] if current_user.openid else current_user.phone}****")
        
        return StandardResponse(
            success=True,
            message="登出成功"
        )
        
    except Exception as e:
        logger.error(f"用户登出失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )