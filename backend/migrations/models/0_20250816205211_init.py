from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    `phone` VARCHAR(20) NOT NULL UNIQUE COMMENT '手机号',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
    `nickname` VARCHAR(50) COMMENT '用户昵称',
    `signature` VARCHAR(200) COMMENT '个性签名',
    `avatar_url` VARCHAR(500) COMMENT '头像URL',
    `gender` VARCHAR(2) COMMENT '性别',
    `height` INT COMMENT '身高(cm)',
    `weight` DOUBLE COMMENT '体重(kg)',
    `body_shape` VARCHAR(4) COMMENT '体型',
    `skin_tone` VARCHAR(3) COMMENT '肤色类型',
    `points` INT NOT NULL COMMENT '积分' DEFAULT 0,
    `latest_session_id` VARCHAR(100) COMMENT '最新会话ID',
    `created_at` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `is_active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='用户信息表';
CREATE TABLE IF NOT EXISTS `user_sessions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `session_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '会话ID',
    `style_analysis_data` JSON COMMENT '风格分析数据',
    `user_analysis_data` JSON COMMENT '用户分析数据',
    `text_analysis_data` JSON COMMENT '文本分析数据',
    `final_recommendation_data` JSON COMMENT '最终推荐数据',
    `personalized_response` LONGTEXT COMMENT '个性化回复',
    `avatar_url` VARCHAR(500) COMMENT '生成的头像URL',
    `is_completed` BOOL NOT NULL COMMENT '是否完成分析' DEFAULT 0,
    `confidence_score` DOUBLE COMMENT '分析置信度',
    `created_at` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT COMMENT '关联用户',
    CONSTRAINT `fk_user_ses_users_c288d510` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='用户会话表';
CREATE TABLE IF NOT EXISTS `wardrobe` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '服饰ID',
    `type` VARCHAR(3) NOT NULL COMMENT '服装类型',
    `name` VARCHAR(100) NOT NULL COMMENT '服饰名称',
    `brand` VARCHAR(50) COMMENT '品牌',
    `color` VARCHAR(30) NOT NULL COMMENT '颜色',
    `size` VARCHAR(20) COMMENT '尺码',
    `material` VARCHAR(100) COMMENT '材质',
    `image_url` VARCHAR(500) NOT NULL COMMENT '服饰图片URL',
    `description` LONGTEXT COMMENT '服饰描述',
    `purchase_price` DECIMAL(10,2) COMMENT '购买价格',
    `purchase_date` DATE COMMENT '购买日期',
    `purchase_place` VARCHAR(100) COMMENT '购买地点',
    `wear_count` INT NOT NULL COMMENT '穿戴次数' DEFAULT 0,
    `last_worn_date` DATE COMMENT '最后穿戴日期',
    `season` VARCHAR(20) COMMENT '适合季节',
    `occasion` VARCHAR(50) COMMENT '适合场合',
    `style_tags` VARCHAR(200) COMMENT '风格标签，逗号分隔',
    `is_favorite` BOOL NOT NULL COMMENT '是否收藏' DEFAULT 0,
    `is_available` BOOL NOT NULL COMMENT '是否可用（未损坏、未丢失等）' DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL COMMENT '添加时间' DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT '所属用户',
    CONSTRAINT `fk_wardrobe_users_c51738cd` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='衣橱表';
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
