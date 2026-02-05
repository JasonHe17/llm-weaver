-- 数据库初始化脚本
-- 创建必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 备注：应用使用SQLAlchemy和Alembic管理表结构
-- 此脚本主要用于创建数据库和基础配置

-- 确保时区设置正确
SET timezone = 'UTC';

-- 创建日志记录表（可选，用于审计）
CREATE TABLE IF NOT EXISTS db_audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    operation VARCHAR(20),
    old_data JSONB,
    new_data JSONB,
    performed_by VARCHAR(100),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
