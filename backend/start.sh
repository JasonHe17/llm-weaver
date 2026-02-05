#!/bin/bash
set -e

echo "=========================================="
echo "LLM Weaver Backend Starting..."
echo "=========================================="

# 等待数据库就绪
echo "Waiting for database..."
until PGPASSWORD=$DB_PASSWORD psql -h postgres -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 2
done
echo "Database is ready!"

# 运行数据库迁移
echo "Running database migrations..."
alembic upgrade head

# 启动应用
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
