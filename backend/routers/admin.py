# routers/admin.py
import os
import json
import aiofiles
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime

from models.extended_models import Product, Influencer, DataChangeLog, ProductCategory, Platform
from models.user_models import StandardResponse, PaginatedResponse
from services.vector_db_service import get_vector_service
from services.sync_service import get_sync_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])

# === 数据模型 ===
class ProductCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    category: ProductCategory
    subcategory: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    description: Optional[str] = None
    features: Optional[str] = None
    materials: Optional[str] = None
    colors: Optional[List[str]] = None
    sizes: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    occasion_tags: Optional[List[str]] = None
    season_tags: Optional[List[str]] = None
    suitable_age_range: Optional[str] = None
    suitable_body_types: Optional[List[str]] = None
    suitable_skin_tones: Optional[List[str]] = None
    purchase_url: Optional[str] = None
    platform: Optional[str] = None

class InfluencerCreate(BaseModel):
    name: str
    platform: Platform
    platform_id: Optional[str] = None
    bio: Optional[str] = None
    age_range: Optional[str] = None
    height: Optional[int] = None
    body_type: Optional[str] = None
    skin_tone: Optional[str] = None
    style_tags: Optional[List[str]] = None
    primary_styles: Optional[List[str]] = None
    content_types: Optional[List[str]] = None
    expertise_areas: Optional[List[str]] = None
    price_range: Optional[str] = None
    target_audience: Optional[List[str]] = None
    suitable_body_types: Optional[List[str]] = None
    suitable_age_ranges: Optional[List[str]] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[float] = None

class VectorSearchRequest(BaseModel):
    query: str
    limit: int = 10

# === 商品管理 ===
@router.post("/products", response_model=StandardResponse)
async def create_product(product_data: ProductCreate):
    """创建商品"""
    try:
        product = await Product.create(**product_data.dict())
        
        logger.info(f"创建商品成功: {product.name} (ID: {product.id})")
        
        return StandardResponse(
            success=True,
            message="商品创建成功",
            data={"product_id": product.id}
        )
        
    except Exception as e:
        logger.error(f"创建商品失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建商品失败"
        )

@router.post("/products/{product_id}/upload-image", response_model=StandardResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    image_type: str = Form("main")  # main, detail1, detail2, etc.
):
    """上传商品图片"""
    try:
        product = await Product.get_or_none(id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        # 验证文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 创建商品图片目录
        product_dir = f"static/products/{product_id}"
        os.makedirs(product_dir, exist_ok=True)
        
        # 生成文件名
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{image_type}{file_extension}"
        file_path = os.path.join(product_dir, filename)
        relative_path = f"products/{product_id}/{filename}"
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 更新商品记录
        if image_type == "main":
            product.main_image = relative_path
        else:
            detail_images = product.detail_images or []
            detail_images.append(relative_path)
            product.detail_images = detail_images
        
        await product.save()
        
        return StandardResponse(
            success=True,
            message="图片上传成功",
            data={"image_path": relative_path}
        )
        
    except Exception as e:
        logger.error(f"上传商品图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="图片上传失败")

@router.get("/products", response_model=PaginatedResponse)
async def get_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[ProductCategory] = None,
    is_active: Optional[bool] = None
):
    """获取商品列表"""
    try:
        query = Product.all()
        
        if category:
            query = query.filter(category=category)
        if is_active is not None:
            query = query.filter(is_active=is_active)
        
        total = await query.count()
        offset = (page - 1) * size
        products = await query.offset(offset).limit(size).order_by('-created_at')
        
        products_data = [product.to_dict() for product in products]
        
        return PaginatedResponse(
            success=True,
            message="获取商品列表成功",
            data=products_data,
            total=total,
            page=page,
            size=size,
            has_next=total > page * size
        )
        
    except Exception as e:
        logger.error(f"获取商品列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取商品列表失败")

@router.put("/products/{product_id}", response_model=StandardResponse)
async def update_product(product_id: int, product_data: ProductCreate):
    """更新商品"""
    try:
        product = await Product.get_or_none(id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        update_data = product_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await product.save()
        
        return StandardResponse(
            success=True,
            message="商品更新成功",
            data=product.to_dict()
        )
        
    except Exception as e:
        logger.error(f"更新商品失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新商品失败")

@router.delete("/products/{product_id}", response_model=StandardResponse)
async def delete_product(product_id: int):
    """删除商品（软删除）"""
    try:
        product = await Product.get_or_none(id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        product.is_active = False
        await product.save()
        
        return StandardResponse(
            success=True,
            message="商品删除成功"
        )
        
    except Exception as e:
        logger.error(f"删除商品失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除商品失败")

# === 博主管理 ===
@router.post("/influencers", response_model=StandardResponse)
async def create_influencer(influencer_data: InfluencerCreate):
    """创建博主"""
    try:
        influencer = await Influencer.create(**influencer_data.dict())
        
        logger.info(f"创建博主成功: {influencer.name} (ID: {influencer.id})")
        
        return StandardResponse(
            success=True,
            message="博主创建成功",
            data={"influencer_id": influencer.id}
        )
        
    except Exception as e:
        logger.error(f"创建博主失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建博主失败")

@router.post("/influencers/{influencer_id}/upload-avatar", response_model=StandardResponse)
async def upload_influencer_avatar(
    influencer_id: int,
    file: UploadFile = File(...)
):
    """上传博主头像"""
    try:
        influencer = await Influencer.get_or_none(id=influencer_id)
        if not influencer:
            raise HTTPException(status_code=404, detail="博主不存在")
        
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 创建博主图片目录
        influencer_dir = f"static/influencers/{influencer_id}"
        os.makedirs(influencer_dir, exist_ok=True)
        
        # 生成文件名
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"avatar{file_extension}"
        file_path = os.path.join(influencer_dir, filename)
        relative_path = f"influencers/{influencer_id}/{filename}"
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 更新博主记录
        influencer.avatar = relative_path
        await influencer.save()
        
        return StandardResponse(
            success=True,
            message="头像上传成功",
            data={"avatar_path": relative_path}
        )
        
    except Exception as e:
        logger.error(f"上传博主头像失败: {str(e)}")
        raise HTTPException(status_code=500, detail="头像上传失败")

@router.get("/influencers", response_model=PaginatedResponse)
async def get_influencers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    platform: Optional[Platform] = None,
    is_active: Optional[bool] = None
):
    """获取博主列表"""
    try:
        query = Influencer.all()
        
        if platform:
            query = query.filter(platform=platform)
        if is_active is not None:
            query = query.filter(is_active=is_active)
        
        total = await query.count()
        offset = (page - 1) * size
        influencers = await query.offset(offset).limit(size).order_by('-created_at')
        
        influencers_data = [influencer.to_dict() for influencer in influencers]
        
        return PaginatedResponse(
            success=True,
            message="获取博主列表成功",
            data=influencers_data,
            total=total,
            page=page,
            size=size,
            has_next=total > page * size
        )
        
    except Exception as e:
        logger.error(f"获取博主列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取博主列表失败")

# === 向量数据库管理 ===
@router.get("/vector-db/status")
async def get_vector_db_status():
    """获取向量数据库状态"""
    try:
        vector_service = get_vector_service()
        sync_service = get_sync_service()
        
        vector_stats = vector_service.get_collection_stats()
        sync_status = await sync_service.get_sync_status()
        
        return {
            "success": True,
            "vector_db": vector_stats,
            "sync_status": sync_status
        }
        
    except Exception as e:
        logger.error(f"获取向量数据库状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取状态失败")

@router.post("/vector-db/search/products")
async def search_products_vector(request: VectorSearchRequest):
    """测试商品向量搜索"""
    try:
        vector_service = get_vector_service()
        results = await vector_service.search_products(request.query, request.limit)
        
        return {
            "success": True,
            "query": request.query,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"商品向量搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败")

@router.post("/vector-db/search/influencers")
async def search_influencers_vector(request: VectorSearchRequest):
    """测试博主向量搜索"""
    try:
        vector_service = get_vector_service()
        results = await vector_service.search_influencers(request.query, request.limit)
        
        return {
            "success": True,
            "query": request.query,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"博主向量搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败")

@router.post("/vector-db/sync/force", response_model=StandardResponse)
async def force_full_sync():
    """强制全量同步向量数据库"""
    try:
        sync_service = get_sync_service()
        result = await sync_service.force_full_sync()
        
        return StandardResponse(
            success=True,
            message="全量同步完成",
            data=result
        )
        
    except Exception as e:
        logger.error(f"强制同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")

@router.post("/vector-db/sync/manual", response_model=StandardResponse)
async def manual_sync():
    """手动处理待处理的同步任务"""
    try:
        sync_service = get_sync_service()
        processed = await sync_service.process_pending_changes()
        
        return StandardResponse(
            success=True,
            message=f"处理了 {processed} 个变更",
            data={"processed_count": processed}
        )
        
    except Exception as e:
        logger.error(f"手动同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail="同步失败")

# === 数据变更日志管理 ===
@router.get("/sync-logs", response_model=PaginatedResponse)
async def get_sync_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    processed: Optional[bool] = None,
    table_name: Optional[str] = None
):
    """获取同步日志"""
    try:
        query = DataChangeLog.all()
        
        if processed is not None:
            query = query.filter(processed=processed)
        if table_name:
            query = query.filter(table_name=table_name)
        
        total = await query.count()
        offset = (page - 1) * size
        logs = await query.offset(offset).limit(size).order_by('-created_at')
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "operation": log.operation,
                "processed": log.processed,
                "processed_at": log.processed_at.isoformat() if log.processed_at else None,
                "error_message": log.error_message,
                "retry_count": log.retry_count,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return PaginatedResponse(
            success=True,
            message="获取同步日志成功",
            data=logs_data,
            total=total,
            page=page,
            size=size,
            has_next=total > page * size
        )
        
    except Exception as e:
        logger.error(f"获取同步日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取日志失败")

# === 前端监控界面 ===
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """管理后台监控界面"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OOTD管理后台</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            h1 {
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }
            
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                text-align: center;
                padding: 20px;
            }
            
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: #3498db;
                margin-bottom: 10px;
            }
            
            .stat-label {
                color: #7f8c8d;
                font-size: 0.9rem;
            }
            
            .actions {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }
            
            .btn {
                padding: 10px 20px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: background 0.3s;
            }
            
            .btn:hover {
                background: #2980b9;
            }
            
            .btn-danger {
                background: #e74c3c;
            }
            
            .btn-danger:hover {
                background: #c0392b;
            }
            
            .btn-success {
                background: #27ae60;
            }
            
            .btn-success:hover {
                background: #219a52;
            }
            
            .search-section {
                margin-bottom: 30px;
            }
            
            .search-form {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            
            .search-input {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            
            .results {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                min-height: 100px;
            }
            
            .result-item {
                background: white;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }
            
            .loading {
                text-align: center;
                color: #7f8c8d;
            }
            
            .error {
                color: #e74c3c;
                background: #fadbd8;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            
            .success {
                color: #27ae60;
                background: #d5f4e6;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 OOTD智能助手管理后台</h1>
            
            <!-- 统计信息 -->
            <div class="stats-grid">
                <div class="card stat-card">
                    <div class="stat-number" id="products-count">-</div>
                    <div class="stat-label">商品总数</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-number" id="influencers-count">-</div>
                    <div class="stat-label">博主总数</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-number" id="pending-sync">-</div>
                    <div class="stat-label">待同步数据</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-number" id="vector-status">-</div>
                    <div class="stat-label">向量数据库状态</div>
                </div>
            </div>
            
            <!-- 操作按钮 -->
            <div class="card">
                <h3>快速操作</h3>
                <div class="actions">
                    <button class="btn" onclick="refreshStatus()">刷新状态</button>
                    <button class="btn btn-success" onclick="manualSync()">手动同步</button>
                    <button class="btn btn-danger" onclick="forceFullSync()">强制全量同步</button>
                    <a href="/docs#/管理后台" class="btn" target="_blank">API文档</a>
                </div>
                <div id="operation-result"></div>
            </div>
            
            <!-- 商品搜索测试 -->
            <div class="card search-section">
                <h3>商品向量搜索测试</h3>
                <div class="search-form">
                    <input type="text" class="search-input" id="product-search" placeholder="输入搜索词，如：优雅的晚礼服">
                    <button class="btn" onclick="searchProducts()">搜索商品</button>
                </div>
                <div class="results" id="product-results">
                    <div class="loading">在这里测试商品搜索功能...</div>
                </div>
            </div>
            
            <!-- 博主搜索测试 -->
            <div class="card search-section">
                <h3>博主向量搜索测试</h3>
                <div class="search-form">
                    <input type="text" class="search-input" id="influencer-search" placeholder="输入搜索词，如：适合职场女性的时尚博主">
                    <button class="btn" onclick="searchInfluencers()">搜索博主</button>
                </div>
                <div class="results" id="influencer-results">
                    <div class="loading">在这里测试博主搜索功能...</div>
                </div>
            </div>
        </div>

        <script>
            // 页面加载时获取状态
            window.onload = function() {
                refreshStatus();
            };

            // 刷新状态
            async function refreshStatus() {
                try {
                    const response = await fetch('/api/admin/vector-db/status');
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('products-count').textContent = data.vector_db.products_count;
                        document.getElementById('influencers-count').textContent = data.vector_db.influencers_count;
                        document.getElementById('pending-sync').textContent = data.sync_status.total_pending;
                        document.getElementById('vector-status').textContent = data.vector_db.status;
                    }
                } catch (error) {
                    console.error('获取状态失败:', error);
                }
            }

            // 手动同步
            async function manualSync() {
                const resultDiv = document.getElementById('operation-result');
                resultDiv.innerHTML = '<div class="loading">正在同步...</div>';
                
                try {
                    const response = await fetch('/api/admin/vector-db/sync/manual', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = `<div class="success">✅ ${data.message}</div>`;
                        setTimeout(refreshStatus, 1000);
                    } else {
                        resultDiv.innerHTML = `<div class="error">❌ 同步失败</div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div class="error">❌ 同步失败: ${error.message}</div>`;
                }
            }

            // 强制全量同步
            async function forceFullSync() {
                if (!confirm('确定要执行强制全量同步吗？这将重置向量数据库并重新同步所有数据。')) {
                    return;
                }
                
                const resultDiv = document.getElementById('operation-result');
                resultDiv.innerHTML = '<div class="loading">正在执行全量同步，请耐心等待...</div>';
                
                try {
                    const response = await fetch('/api/admin/vector-db/sync/force', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = `<div class="success">✅ 全量同步完成<br>商品: ${data.data.products_synced}/${data.data.total_products}<br>博主: ${data.data.influencers_synced}/${data.data.total_influencers}</div>`;
                        setTimeout(refreshStatus, 1000);
                    } else {
                        resultDiv.innerHTML = `<div class="error">❌ 全量同步失败</div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div class="error">❌ 全量同步失败: ${error.message}</div>`;
                }
            }

            // 搜索商品
            async function searchProducts() {
                const query = document.getElementById('product-search').value;
                if (!query.trim()) {
                    alert('请输入搜索词');
                    return;
                }
                
                const resultsDiv = document.getElementById('product-results');
                resultsDiv.innerHTML = '<div class="loading">搜索中...</div>';
                
                try {
                    const response = await fetch('/api/admin/vector-db/search/products', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({query: query, limit: 5})
                    });
                    const data = await response.json();
                    
                    if (data.success && data.results.length > 0) {
                        let html = '';
                        data.results.forEach((result, index) => {
                            const similarity = ((1 - result.distance) * 100).toFixed(1);
                            html += `
                                <div class="result-item">
                                    <strong>商品 ${result.id}</strong> (相似度: ${similarity}%)
                                    <br><strong>名称:</strong> ${result.metadata.name || 'N/A'}
                                    <br><strong>品牌:</strong> ${result.metadata.brand || 'N/A'}
                                    <br><strong>类别:</strong> ${result.metadata.category || 'N/A'}
                                    <br><strong>价格:</strong> ¥${result.metadata.price || 'N/A'}
                                </div>
                            `;
                        });
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = '<div class="loading">未找到相关商品</div>';
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
                }
            }

            // 搜索博主
            async function searchInfluencers() {
                const query = document.getElementById('influencer-search').value;
                if (!query.trim()) {
                    alert('请输入搜索词');
                    return;
                }
                
                const resultsDiv = document.getElementById('influencer-results');
                resultsDiv.innerHTML = '<div class="loading">搜索中...</div>';
                
                try {
                    const response = await fetch('/api/admin/vector-db/search/influencers', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({query: query, limit: 5})
                    });
                    const data = await response.json();
                    
                    if (data.success && data.results.length > 0) {
                        let html = '';
                        data.results.forEach((result, index) => {
                            const similarity = ((1 - result.distance) * 100).toFixed(1);
                            html += `
                                <div class="result-item">
                                    <strong>博主 ${result.id}</strong> (相似度: ${similarity}%)
                                    <br><strong>名称:</strong> ${result.metadata.name || 'N/A'}
                                    <br><strong>平台:</strong> ${result.metadata.platform || 'N/A'}
                                    <br><strong>年龄段:</strong> ${result.metadata.age_range || 'N/A'}
                                    <br><strong>体型:</strong> ${result.metadata.body_type || 'N/A'}
                                    <br><strong>粉丝数:</strong> ${result.metadata.followers_count || 'N/A'}
                                </div>
                            `;
                        });
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = '<div class="loading">未找到相关博主</div>';
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
                }
            }

            // 回车键搜索
            document.getElementById('product-search').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchProducts();
                }
            });

            document.getElementById('influencer-search').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchInfluencers();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)