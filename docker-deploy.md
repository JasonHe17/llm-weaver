# 快速启动指南

## 使用 Docker Compose 启动

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

### 2. 启动服务

```bash
# 启动核心服务（数据库、Redis、后端、前端）
docker-compose up -d

# 启动包含监控的服务
docker-compose --profile monitoring up -d

# 启动包含Nginx的服务（生产环境）
docker-compose --profile production up -d

# 启动所有服务
docker-compose --profile production --profile monitoring up -d
```

### 3. 初始化数据库

```bash
# 创建管理员用户
docker-compose exec backend python scripts/create_admin.py
```

### 4. 访问服务

- 前端界面: http://localhost:8080
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090 (需要 --profile monitoring)
- Grafana: http://localhost:3000 (需要 --profile monitoring)

## 服务说明

| 服务 | 描述 | 端口 |
|------|------|------|
| postgres | PostgreSQL数据库 | 5432 |
| redis | Redis缓存 | 6379 |
| backend | FastAPI后端服务 | 8000 |
| frontend | Vue3前端(Nginx) | 8080 |
| nginx | 反向代理(可选) | 80/443 |
| celery-worker | 异步任务处理 | - |
| celery-beat | 定时任务调度 | - |
| prometheus | 指标收集 | 9090 |
| grafana | 监控面板 | 3000 |

## 常用命令

```bash
# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart backend

# 停止服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v

# 进入容器
docker-compose exec backend bash
docker-compose exec postgres psql -U llm_weaver

# 数据库迁移
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic upgrade head
```
