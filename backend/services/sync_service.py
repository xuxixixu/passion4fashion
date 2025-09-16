# services/sync_service.py
import asyncio
import logging
from typing import List
from datetime import datetime, timezone

from models.extended_models import DataChangeLog, Product, Influencer
from services.vector_db_service import get_vector_service

logger = logging.getLogger(__name__)

class DataSyncService:
    """数据同步服务 - 处理触发器产生的变更日志"""
    
    def __init__(self):
        self.vector_service = get_vector_service()
        self.max_retry_count = 3
    
    async def process_pending_changes(self) -> int:
        """处理所有待处理的变更"""
        try:
            # 获取未处理的变更日志
            pending_changes = await DataChangeLog.filter(
                processed=False,
                retry_count__lt=self.max_retry_count
            ).order_by('created_at').limit(100)
            
            if not pending_changes:
                return 0
            
            processed_count = 0
            
            for change in pending_changes:
                try:
                    success = await self._process_single_change(change)
                    
                    if success:
                        change.processed = True
                        change.processed_at = datetime.now(timezone.utc)
                        change.error_message = None
                        processed_count += 1
                        logger.info(f"成功处理变更: {change.table_name} {change.record_id} {change.operation}")
                    else:
                        change.retry_count += 1
                        change.error_message = "处理失败，已重试"
                        logger.warning(f"处理变更失败，将重试: {change.table_name} {change.record_id}")
                    
                    await change.save()
                    
                except Exception as e:
                    change.retry_count += 1
                    change.error_message = str(e)
                    await change.save()
                    logger.error(f"处理变更时出现错误: {str(e)}")
            
            logger.info(f"处理了 {processed_count}/{len(pending_changes)} 个变更")
            return processed_count
            
        except Exception as e:
            logger.error(f"批量处理变更失败: {str(e)}")
            return 0
    
    async def _process_single_change(self, change: DataChangeLog) -> bool:
        """处理单个变更"""
        try:
            if change.table_name == "products":
                return await self._process_product_change(change)
            elif change.table_name == "influencers":
                return await self._process_influencer_change(change)
            else:
                logger.warning(f"未知的表名: {change.table_name}")
                return False
                
        except Exception as e:
            logger.error(f"处理单个变更失败: {str(e)}")
            return False
    
    async def _process_product_change(self, change: DataChangeLog) -> bool:
        """处理商品变更"""
        try:
            if change.operation == "DELETE":
                # 删除操作
                return self.vector_service.delete_product(change.record_id)
            
            elif change.operation in ["INSERT", "UPDATE"]:
                # 插入或更新操作
                product = await Product.get_or_none(id=change.record_id)
                if not product:
                    logger.warning(f"商品 {change.record_id} 不存在，可能已被删除")
                    return True  # 认为处理成功，避免重复处理
                
                if not product.is_active:
                    # 如果商品已停用，从向量数据库删除
                    return self.vector_service.delete_product(change.record_id)
                
                product_data = product.to_dict()
                
                if change.operation == "INSERT":
                    return await self.vector_service.add_product(product_data)
                else:  # UPDATE
                    return await self.vector_service.update_product(product_data)
            
            return False
            
        except Exception as e:
            logger.error(f"处理商品变更失败: {str(e)}")
            return False
    
    async def _process_influencer_change(self, change: DataChangeLog) -> bool:
        """处理博主变更"""
        try:
            if change.operation == "DELETE":
                # 删除操作
                return self.vector_service.delete_influencer(change.record_id)
            
            elif change.operation in ["INSERT", "UPDATE"]:
                # 插入或更新操作
                influencer = await Influencer.get_or_none(id=change.record_id)
                if not influencer:
                    logger.warning(f"博主 {change.record_id} 不存在，可能已被删除")
                    return True
                
                if not influencer.is_active:
                    # 如果博主已停用，从向量数据库删除
                    return self.vector_service.delete_influencer(change.record_id)
                
                influencer_data = influencer.to_dict()
                
                if change.operation == "INSERT":
                    return await self.vector_service.add_influencer(influencer_data)
                else:  # UPDATE
                    return await self.vector_service.update_influencer(influencer_data)
            
            return False
            
        except Exception as e:
            logger.error(f"处理博主变更失败: {str(e)}")
            return False
    
    async def cleanup_old_logs(self, days: int = 7) -> int:
        """清理旧的日志记录"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # 删除已处理且较旧的日志
            deleted_count = await DataChangeLog.filter(
                processed=True,
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f"清理了 {deleted_count} 条旧日志记录")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {str(e)}")
            return 0
    
    async def get_sync_status(self) -> dict:
        """获取同步状态"""
        try:
            total_pending = await DataChangeLog.filter(processed=False).count()
            failed_count = await DataChangeLog.filter(
                processed=False,
                retry_count__gte=self.max_retry_count
            ).count()
            
            recent_processed = await DataChangeLog.filter(
                processed=True,
                processed_at__gte=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            ).count()
            
            return {
                "total_pending": total_pending,
                "failed_count": failed_count,
                "recent_processed": recent_processed,
                "vector_db_stats": self.vector_service.get_collection_stats()
            }
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {str(e)}")
            return {
                "total_pending": 0,
                "failed_count": 0,
                "recent_processed": 0,
                "error": str(e)
            }
    
    async def force_full_sync(self) -> dict:
        """强制全量同步（谨慎使用）"""
        try:
            logger.info("开始强制全量同步...")
            
            # 重置向量数据库
            self.vector_service.reset_collections()
            
            # 同步所有活跃商品
            products = await Product.filter(is_active=True)
            product_success = 0
            for product in products:
                try:
                    success = await self.vector_service.add_product(product.to_dict())
                    if success:
                        product_success += 1
                except Exception as e:
                    logger.error(f"同步商品 {product.id} 失败: {str(e)}")
            
            # 同步所有活跃博主
            influencers = await Influencer.filter(is_active=True)
            influencer_success = 0
            for influencer in influencers:
                try:
                    success = await self.vector_service.add_influencer(influencer.to_dict())
                    if success:
                        influencer_success += 1
                except Exception as e:
                    logger.error(f"同步博主 {influencer.id} 失败: {str(e)}")
            
            # 清理所有变更日志
            await DataChangeLog.all().delete()
            
            result = {
                "products_synced": product_success,
                "influencers_synced": influencer_success,
                "total_products": len(products),
                "total_influencers": len(influencers)
            }
            
            logger.info(f"全量同步完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"强制全量同步失败: {str(e)}")
            return {"error": str(e)}

# 全局同步服务实例
_sync_service = None

def get_sync_service() -> DataSyncService:
    """获取同步服务单例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = DataSyncService()
    return _sync_service

# 后台任务函数
async def run_sync_worker():
    """后台同步工作线程"""
    sync_service = get_sync_service()
    
    while True:
        try:
            # 处理待处理的变更
            processed = await sync_service.process_pending_changes()
            
            if processed > 0:
                logger.info(f"同步任务处理了 {processed} 个变更")
            
            # 每小时清理一次旧日志
            import time
            if int(time.time()) % 3600 < 60:  # 每小时的前1分钟执行
                await sync_service.cleanup_old_logs()
            
            # 等待60秒后再次检查
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"同步工作线程出现错误: {str(e)}")
            await asyncio.sleep(300)  # 出错时等待5分钟再重试