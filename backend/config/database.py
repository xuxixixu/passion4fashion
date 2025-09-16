import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DATABASE_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "3306")),
                "user": os.getenv("DB_USER", "root"),
                "password": os.getenv("DB_PASSWORD", ""),
                "database": os.getenv("DB_NAME", "fashion"),
                "charset": "utf8mb4",
                "echo": os.getenv("DB_ECHO", "False").lower() == "true"
            }
        }
    },
    "apps": {
        "models": {
            "models": ["models.database_models","models.extended_models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai"
}

# Aerich配置（用于数据库迁移）
AERICH_CONFIG = {
    "tortoise_orm": DATABASE_CONFIG
}