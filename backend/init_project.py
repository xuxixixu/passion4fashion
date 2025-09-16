#!/usr/bin/env python
# init_project.py - 项目初始化脚本

import os
import sys
from pathlib import Path

def create_directories():
    """创建项目所需的目录结构"""
    directories = [
        "static",
        "static/products", 
        "static/influencers",
        "user_data",
        "user_data/avatars",
        "user_data/advice_based_on_userdata", 
        "vector_db",
        "logs"
    ]
    
    print("🚀 正在初始化项目目录结构...")
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    # 创建空的 .gitkeep 文件，确保空目录被git跟踪
    gitkeep_dirs = ["static/products", "static/influencers", "user_data/avatars", "vector_db"]
    for directory in gitkeep_dirs:
        gitkeep_file = os.path.join(directory, ".gitkeep")
        if not os.path.exists(gitkeep_file):
            Path(gitkeep_file).touch()
            print(f"📝 创建 .gitkeep: {gitkeep_file}")

def check_env_file():
    """检查环境变量文件"""
    if not os.path.exists(".env"):
        print("⚠️  .env 文件不存在")
        if os.path.exists(".env.example"):
            print("💡 请复制 .env.example 到 .env 并配置相关参数")
            print("   cp .env.example .env")
        else:
            print("💡 请创建 .env 文件并配置以下参数:")
            print("""
# 数据库配置
DATABASE_URL=mysql://username:password@localhost:3306/ootd_fashion_db

# JWT配置  
JWT_SECRET_KEY=your-super-secret-jwt-key

# API密钥
DOUBAO_API_KEY=your-doubao-api-key
OPENROUTER_API_KEY=your-openrouter-api-key

# 抖音小程序（可选）
DOUYIN_APP_ID=your-douyin-app-id
DOUYIN_APP_SECRET=your-douyin-app-secret
            """)
        return False
    else:
        print("✅ .env 文件已存在")
        return True

def check_dependencies():
    """检查依赖包"""
    try:
        import fastapi
        import tortoise
        import chromadb
        import langchain
        print("✅ 核心依赖包检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("💡 请运行: pip install -r requirements.txt")
        return False

def main():
    """主函数"""
    print("🎨 OOTD智能时尚助手 - 项目初始化")
    print("=" * 50)
    
    # 创建目录
    create_directories()
    print()
    
    # 检查环境变量
    env_ok = check_env_file()
    print()
    
    # 检查依赖
    deps_ok = check_dependencies()
    print()
    
    if env_ok and deps_ok:
        print("🎉 项目初始化完成！可以运行以下命令启动应用:")
        print("   python main.py")
        print()
        print("📊 启动后可访问:")
        print("   - API文档: http://localhost/docs")
        print("   - 管理后台: http://localhost/api/admin/dashboard")
        print("   - 健康检查: http://localhost/health")
    else:
        print("⚠️  项目初始化未完成，请先解决上述问题")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())