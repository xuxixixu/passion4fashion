# services/file_service.py
import uuid
import os
import shutil
from fastapi import UploadFile, HTTPException
from typing import Optional, List
from pathlib import Path

class FileService:
    """文件服务类，处理所有文件上传、存储、删除操作"""
    
    def __init__(self, base_dir: str = "user_data"):
        self.base_dir = Path(base_dir)
        self.avatar_dir = self.base_dir / "avatars"
        self.wardrobe_dir = self.base_dir / "wardrobe"
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        self.base_dir.mkdir(exist_ok=True)
        self.avatar_dir.mkdir(exist_ok=True)
        self.wardrobe_dir.mkdir(exist_ok=True)
    
    def _validate_file(self, file: UploadFile, max_size: int = 10 * 1024 * 1024):
        """验证文件格式和大小"""
        # 允许的图片格式
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        allowed_content_types = {
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/gif', 'image/webp'
        }
        
        # 检查文件类型
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 检查文件扩展名
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件扩展名: {file_extension}"
            )
        
        return file_extension
    
    def _generate_filename(self, prefix: str, user_id: int, extension: str, item_id: Optional[int] = None) -> str:
        """生成唯一的文件名"""
        unique_id = uuid.uuid4().hex[:8]
        if item_id:
            return f"{prefix}_{user_id}_{item_id}_{unique_id}{extension}"
        return f"{prefix}_{user_id}_{unique_id}{extension}"
    
    async def save_avatar(self, user_id: int, file: UploadFile) -> str:
        """
        保存用户头像
        
        Args:
            user_id: 用户ID
            file: 上传的文件
            
        Returns:
            str: 保存的文件名
        """
        try:
            # 验证文件
            extension = self._validate_file(file)
            
            # 生成文件名
            filename = self._generate_filename("avatar", user_id, extension)
            
            # 保存文件
            file_path = self.avatar_dir / filename
            
            # 读取文件内容并保存
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            return filename
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"保存头像失败: {str(e)}")
    
    async def save_wardrobe_image(self, user_id: int, item_id: int, file: UploadFile) -> str:
        """
        保存衣橱物品图片
        
        Args:
            user_id: 用户ID
            item_id: 物品ID
            file: 上传的文件
            
        Returns:
            str: 保存的文件名
        """
        try:
            # 验证文件
            extension = self._validate_file(file)
            
            # 生成文件名
            filename = self._generate_filename("wardrobe", user_id, extension, item_id)
            
            # 保存文件
            file_path = self.wardrobe_dir / filename
            
            # 读取文件内容并保存
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            return filename
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"保存衣橱图片失败: {str(e)}")
    
    def delete_file(self, file_type: str, filename: str) -> bool:
        """
        删除文件
        
        Args:
            file_type: 文件类型 ('avatars' 或 'wardrobe')
            filename: 文件名
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if file_type == 'avatars':
                file_path = self.avatar_dir / filename
            elif file_type == 'wardrobe':
                file_path = self.wardrobe_dir / filename
            else:
                return False
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
            
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    def get_file_path(self, file_type: str, filename: str) -> Optional[Path]:
        """
        获取文件的完整路径
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            Path: 文件路径，如果文件不存在返回None
        """
        if not filename:
            return None
            
        if file_type == 'avatars':
            file_path = self.avatar_dir / filename
        elif file_type == 'wardrobe':
            file_path = self.wardrobe_dir / filename
        else:
            return None
        
        return file_path if file_path.exists() else None
    
    def build_file_url(self, file_type: str, filename: str, base_url: str = "") -> str:
        """
        构建文件访问URL
        
        Args:
            file_type: 文件类型
            filename: 文件名
            base_url: 基础URL
            
        Returns:
            str: 完整的文件URL
        """
        if not filename:
            return ""
        
        # 移除base_url末尾的斜杠
        base_url = base_url.rstrip('/')
        
        return f"{base_url}/static/{file_type}/{filename}"
    
    def cleanup_user_files(self, user_id: int):
        """
        清理用户的所有文件（用户删除时调用）
        
        Args:
            user_id: 用户ID
        """
        try:
            # 删除用户头像
            for file_path in self.avatar_dir.glob(f"avatar_{user_id}_*"):
                file_path.unlink()
            
            # 删除用户衣橱图片
            for file_path in self.wardrobe_dir.glob(f"wardrobe_{user_id}_*"):
                file_path.unlink()
                
        except Exception as e:
            print(f"清理用户文件失败: {e}")
    
    def get_storage_stats(self) -> dict:
        """
        获取存储统计信息
        
        Returns:
            dict: 存储统计信息
        """
        try:
            avatar_count = len(list(self.avatar_dir.glob("*.jpg"))) + \
                          len(list(self.avatar_dir.glob("*.png"))) + \
                          len(list(self.avatar_dir.glob("*.gif"))) + \
                          len(list(self.avatar_dir.glob("*.webp")))
            
            wardrobe_count = len(list(self.wardrobe_dir.glob("*.jpg"))) + \
                            len(list(self.wardrobe_dir.glob("*.png"))) + \
                            len(list(self.wardrobe_dir.glob("*.gif"))) + \
                            len(list(self.wardrobe_dir.glob("*.webp")))
            
            # 计算文件夹大小
            def get_size(path):
                total = 0
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        total += file_path.stat().st_size
                return total
            
            avatar_size = get_size(self.avatar_dir)
            wardrobe_size = get_size(self.wardrobe_dir)
            
            return {
                "avatar_files": avatar_count,
                "wardrobe_files": wardrobe_count,
                "avatar_size_mb": round(avatar_size / 1024 / 1024, 2),
                "wardrobe_size_mb": round(wardrobe_size / 1024 / 1024, 2),
                "total_files": avatar_count + wardrobe_count,
                "total_size_mb": round((avatar_size + wardrobe_size) / 1024 / 1024, 2)
            }
            
        except Exception as e:
            print(f"获取存储统计失败: {e}")
            return {}

# 创建全局文件服务实例
file_service = FileService()