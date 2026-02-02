# 部署指南

## 部署模式

### 1. Docker Compose (推荐开发/测试)

最快速、最简单的部署方式。

#### 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 20GB+ 磁盘空间

#### 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/llm-weaver.git
cd llm-weaver

# 2. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f backend

# 5. 访问服务
# 前端: http://localhost:8080
# 后端API: http://localhost:8000
```

#### 环境变量配置

```bash
# 数据库配置
DB_USER=llm_weaver
DB_PASSWORD=your_secure_password
DB_NAME=llm_weaver
DB_PORT=5432

# Redis配置
REDIS_PORT=6379
REDIS_MAXMEMORY=256mb

# 应用配置
SECRET_KEY=your_random_secret_key  # 用于JWT签名
ENCRYPTION_KEY=your_encryption_key  # 用于数据加密
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:8080,https://your-domain.com

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=8080
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# 监控配置 (可选)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

### 2. Docker Compose + 监控栈

包含Prometheus和Grafana的完整监控方案。

```bash
# 启动基础服务 + 监控
docker-compose --profile monitoring up -d

# 访问Grafana: http://localhost:3000
# 默认账号: admin/admin
```

### 3. 生产环境部署 (Docker Compose + Nginx)

```bash
# 启动生产模式 (包含Nginx反向代理)
docker-compose --profile production up -d
```

Nginx配置文件:

```nginx
# nginx/conf.d/default.conf
server {
    listen 80;
    server_name your-domain.com;
    
    # HTTP重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # OpenAI兼容接口
    location /v1/ {
        proxy_pass http://backend:8000/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # SSE流式响应支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### 4. Kubernetes 部署

适用于大规模生产环境。

```bash
# 应用K8s配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

## SSL证书配置

### Let's Encrypt (免费)

```bash
# 使用Certbot获取证书
docker run -it --rm \
  -v ./nginx/ssl:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  -d your-domain.com
```

### 使用Cloudflare Origin证书

1. 在Cloudflare Dashboard生成Origin证书
2. 下载证书和私钥
3. 放置到 `nginx/ssl/` 目录

## 数据库备份与恢复

### 自动备份 (CronJob)

```bash
# 创建备份脚本
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker exec llm-weaver-db pg_dump -U llm_weaver llm_weaver > $BACKUP_DIR/backup_$DATE.sql

# 保留最近30天的备份
find $BACKUP_DIR -name "backup_*.sql" -mtime +30 -delete
```

### 手动备份

```bash
docker exec llm-weaver-db pg_dump -U llm_weaver llm_weaver > backup.sql
```

### 恢复备份

```bash
docker exec -i llm-weaver-db psql -U llm_weaver llm_weaver < backup.sql
```

## 升级指南

### 平滑升级步骤

```bash
# 1. 备份数据
docker exec llm-weaver-db pg_dump -U llm_weaver llm_weaver > backup_$(date +%Y%m%d).sql

# 2. 拉取最新代码
git pull origin main

# 3. 更新镜像
docker-compose pull

# 4. 执行数据库迁移
docker-compose run --rm backend alembic upgrade head

# 5. 重启服务
docker-compose up -d

# 6. 验证服务
curl http://localhost:8000/api/v1/health
```

## 性能调优

### 数据库优化

```sql
-- 连接数配置 (postgresql.conf)
max_connections = 200
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
work_mem = 10MB
```

### 应用优化

```bash
# 启动更多worker进程
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # 运行3个实例
```

### Redis优化

```bash
# 增加内存限制
REDIS_MAXMEMORY=512mb
```

## 故障排查

### 查看服务状态

```bash
docker-compose ps
docker-compose logs backend
docker-compose logs postgres
```

### 数据库连接问题

```bash
# 检查数据库健康状态
docker-compose exec postgres pg_isready -U llm_weaver

# 进入数据库
docker-compose exec postgres psql -U llm_weaver -d llm_weaver
```

### 重置服务

```bash
# 停止并删除所有容器和数据 (慎用!)
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 安全加固

1. **修改默认密码**: 立即修改数据库、管理后台的默认密码
2. **启用防火墙**: 只开放必要的端口 (80, 443)
3. **定期更新**: 保持系统和依赖项更新
4. **日志监控**: 配置日志告警，监控异常请求
5. **HTTPS**: 生产环境必须使用HTTPS

## 高可用部署

### 架构

```
                    ┌─────────────┐
                    │   CDN       │
                    │ (Cloudflare)│
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
    │  Backend 1  │ │  Backend 2  │ │  Backend 3  │
    │  (FastAPI)  │ │  (FastAPI)  │ │  (FastAPI)  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────┴──────┐           ┌──────┴──────┐
       │ PostgreSQL  │           │    Redis    │
       │   Primary   │◄─────────►│   Cluster   │
       └─────────────┘           └─────────────┘
```

### 实现步骤

1. 使用外部负载均衡器 (AWS ALB, Nginx Plus)
2. 配置数据库主从复制
3. Redis使用Cluster模式或Sentinel
4. 共享文件存储 (S3, NFS) 用于日志和备份
