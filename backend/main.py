# main.py - 更新版本，集成向量数据库和虚拟试穿功能
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from routers import style_analysis, users, wardrobe, auth, ootd, admin, virtual_tryon
from config.database import DATABASE_CONFIG
from services.sync_service import run_sync_worker
import uvicorn
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 后台任务管理
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("启动后台同步服务...")
    
    # 创建后台同步任务
    sync_task = asyncio.create_task(run_sync_worker())
    background_tasks.add(sync_task)
    sync_task.add_done_callback(background_tasks.discard)
    
    # 确保必要的目录存在
    directories = [
        "static",
        "static/products",
        "static/influencers", 
        "user_data",
        "user_data/avatars",
        "user_data/advice_based_on_userdata",
        "user_data/virtual_tryon",
        "vector_db"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"确保目录存在: {directory}")
    
    yield
    
    # 关闭时执行
    logger.info("正在关闭后台服务...")
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

# 创建FastAPI应用
app = FastAPI(
    title="OOTD智能时尚助手API",
    description="基于向量数据库和AI的智能时尚推荐系统 - 支持商品推荐、博主推荐、个性化穿搭建议和虚拟试穿",
    version="4.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 - 严格按照用户要求添加虚拟试穿
app.include_router(auth.router)             # OpenID认证路由
app.include_router(style_analysis.router)  # 风格分析路由
app.include_router(users.router)           # 用户管理路由
app.include_router(wardrobe.router)        # 衣橱管理路由
app.include_router(ootd.router)            # OOTD智能助手路由
app.include_router(admin.router)           # 管理后台路由
app.include_router(virtual_tryon.router)   # 虚拟试穿路由 - 按用户算法实现

# 确保静态文件目录存在并挂载静态文件服务
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册数据库 - 需要包含新增的模型
register_tortoise(
    app,
    config={
        **DATABASE_CONFIG,
        "apps": {
            "models": {
                "models": [
                    "models.database_models",
                    "models.extended_models",  # 新增的模型
                    "aerich.models"
                ],
                "default_connection": "default",
            }
        }
    },
    generate_schemas=True,
    add_exception_handlers=True,
)

@app.get("/")
async def root():
    return {
        "message": "OOTD智能时尚助手API服务",
        "version": "4.1.0",
        "new_features": {
            "向量数据库": "支持商品和博主的语义搜索",
            "商品推荐": "基于用户需求的智能商品推荐",
            "博主推荐": "匹配用户特征的时尚博主推荐",
            "管理后台": "完整的数据管理和监控界面",
            "自动同步": "MySQL触发器自动同步向量数据库",
            "虚拟试穿": "严格按照用户算法实现的AI虚拟试穿功能"
        },
        "auth_methods": {
            "openid": "OpenID静默认证（推荐）",
            "traditional": "传统手机号+密码认证（兼容）"
        },
        "core_features": [
            "🆕 AI虚拟试穿 - 严格按照用户算法：本地存储+批量传输+绿框标识+Gemini生成",
            "🆕 智能商品推荐 - 基于豆包embedding模型的语义搜索",
            "🆕 博主推荐系统 - 匹配用户特征推荐合适的时尚博主",
            "🆕 管理后台界面 - 商品/博主数据管理和向量搜索测试",
            "🔄 自动数据同步 - MySQL触发器驱动的向量数据库同步",
            "👤 用户注册登录 - OpenID和传统认证双重支持",
            "👗 衣橱管理 - 个人服饰管理和穿戴统计",
            "🎨 风格分析 - AI驱动的个性化时尚建议",
            "🤖 OOTD智能助手 - 多模态对话和个性化穿搭推荐",
            "📱 抖音小程序集成 - 完整支持抖音开放平台"
        ],
        "endpoints": {
            "virtual_tryon": {
                "upload_batch": "/api/virtual-tryon/upload-batch",
                "result": "/api/virtual-tryon/result/{session_id}",
                "result_image": "/api/virtual-tryon/result-image/{filename}",
                "cleanup": "/api/virtual-tryon/session/{session_id}"
            },
            "openid_auth": "/api/auth/openid-login",
            "ootd_chat": "/api/ootd/chat",
            "admin_dashboard": "/api/admin/dashboard",
            "vector_search": {
                "products": "/api/admin/vector-db/search/products",
                "influencers": "/api/admin/vector-db/search/influencers"
            },
            "data_management": {
                "products": "/api/admin/products",
                "influencers": "/api/admin/influencers",
                "sync_status": "/api/admin/vector-db/status"
            }
        },
        "technical_stack": {
            "backend": "FastAPI + Tortoise ORM + MySQL",
            "vector_db": "ChromaDB (轻量级向量数据库)",
            "embedding": "豆包 doubao-embedding-vision-250615",
            "ai_agent": "LangChain + OpenAI GPT",
            "virtual_tryon": "用户指定算法：Gemini 2.5 Flash + 绿框标识 + 批量传输",
            "sync_mechanism": "MySQL触发器 + 后台任务"
        },
        "user_algorithm_implementation": {
            "image_storage": "客户端本地存储",
            "transmission": "大文件批量传输方法",
            "user_identification": "绿框标识用户图片",
            "model": "google/gemini-2.5-flash-image-preview",
            "api_reference": "严格按照1.py和2.py的调用方式",
            "polling": "前端轮询获取结果",
            "session_management": "会话ID匹配机制"
        },
        "docs": "/docs",
        "admin": "/api/admin/dashboard"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ootd-fashion-assistant",
        "version": "4.1.0",
        "features": {
            "auth": "enabled",
            "vector_db": "enabled", 
            "auto_sync": "running",
            "admin_panel": "enabled",
            "virtual_tryon": "enabled - user algorithm implementation"
        }
    }

@app.get("/config-check")
async def config_check():
    """检查关键配置状态"""
    # 检查环境变量
    douyin_app_id = os.getenv("DOUYIN_APP_ID", "")
    douyin_app_secret = os.getenv("DOUYIN_APP_SECRET", "")
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    openai_api_key = os.getenv("OPENROUTER_API_KEY", "")
    doubao_api_key = os.getenv("DOUBAO_API_KEY", "")
    
    # 检查向量数据库
    try:
        from services.vector_db_service import get_vector_service
        vector_service = get_vector_service()
        vector_stats = vector_service.get_collection_stats()
        vector_healthy = vector_stats.get("status") == "healthy"
    except Exception as e:
        vector_healthy = False
        vector_stats = {"error": str(e)}
    
    return {
        "environment_config": {
            "douyin_configured": bool(douyin_app_id and douyin_app_secret),
            "jwt_configured": bool(jwt_secret),
            "openai_configured": bool(openai_api_key),
            "doubao_configured": bool(doubao_api_key),
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        "vector_database": {
            "status": "healthy" if vector_healthy else "error",
            "stats": vector_stats
        },
        "directories": {
            "static": os.path.exists("static"),
            "vector_db": os.path.exists("vector_db"),
            "user_data": os.path.exists("user_data"),
            "virtual_tryon": os.path.exists("user_data/virtual_tryon")
        },
        "background_tasks": {
            "sync_worker": len(background_tasks) > 0
        },
        "virtual_tryon_algorithm": {
            "implementation": "user_specified",
            "features": [
                "本地图片存储",
                "批量传输",
                "绿框用户标识", 
                "Gemini 2.5 Flash生成",
                "会话轮询机制"
            ]
        }
    }

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 OOTD智能时尚助手启动中...")
    
    # 检查关键配置
    doubao_api_key = os.getenv("DOUBAO_API_KEY", "")
    openai_api_key = os.getenv("OPENROUTER_API_KEY", "")
    
    if not doubao_api_key:
        logger.warning("⚠️  豆包API密钥未配置，向量embedding功能将受限")
        logger.warning("   请设置环境变量 DOUBAO_API_KEY")
    else:
        logger.info(f"✅ 豆包API密钥已配置: {doubao_api_key[:8]}****")
    
    if not openai_api_key:
        logger.warning("⚠️  OpenRouter API密钥未配置，AI对话和虚拟试穿功能将受限")
        logger.warning("   请设置环境变量 OPENROUTER_API_KEY")
    else:
        logger.info(f"✅ OpenRouter API密钥已配置: {openai_api_key[:8]}****")
    
    # 初始化向量数据库
    try:
        from services.vector_db_service import get_vector_service
        vector_service = get_vector_service()
        stats = vector_service.get_collection_stats()
        logger.info(f"✅ 向量数据库已初始化 - 商品: {stats['products_count']}, 博主: {stats['influencers_count']}")
    except Exception as e:
        logger.error(f"❌ 向量数据库初始化失败: {str(e)}")
    
    # 检查虚拟试穿相关依赖
    try:
        import PIL
        logger.info("✅ PIL图片处理库已就绪")
    except ImportError:
        logger.warning("⚠️  PIL库未安装，虚拟试穿功能可能受限")
    
    logger.info("✅ 系统组件状态:")
    logger.info("  📱 抖音小程序认证系统 - 就绪")
    logger.info("  👤 用户管理系统 - 就绪")
    logger.info("  👗 衣橱管理系统 - 就绪")
    logger.info("  🎨 风格分析系统 - 就绪")
    logger.info("  🤖 OOTD智能助手 - 就绪")
    logger.info("  🗃️  向量数据库 - 就绪")
    logger.info("  🔄 自动同步服务 - 启动中")
    logger.info("  🛠️  管理后台 - 就绪")
    logger.info("  🎭 AI虚拟试穿 - 就绪（用户指定算法）")
    logger.info("🎉 OOTD智能时尚助手启动完成！")
    logger.info("📊 管理后台地址: http://localhost/api/admin/dashboard")
    logger.info("🎭 虚拟试穿API: http://localhost/api/virtual-tryon/upload-batch")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🔄 OOTD智能时尚助手正在关闭...")
    logger.info("✅ 服务已安全关闭")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )