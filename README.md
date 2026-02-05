# LLM Weaver 🧵

一个功能强大、高性能的LLM API中转服务平台，支持多供应商统一管理、智能路由、费用控制和全面监控。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.4%2B-4FC08D.svg)](https://vuejs.org/)

## ✨ 核心特性

- **🔌 多供应商支持**：OpenAI、Anthropic、Google Gemini、Azure OpenAI、本地模型等
- **🎯 OpenAI兼容**：完全兼容OpenAI API格式，无缝迁移现有应用
- **🧠 智能路由**：基于成本、延迟、可用性的智能路由策略
- **💰 费用控制**：API Key管理、预算限制、实时用量统计
- **⚡ 高性能**：异步架构、连接池、多级缓存，支持高并发
- **🔒 企业级安全**：JWT认证、IP白名单、请求签名、敏感信息加密
- **📊 全面监控**：实时监控、告警通知、详细日志分析
- **🎨 美观前端**：Vue3 + TypeScript + Element Plus，现代化的管理界面

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Web管理    │  │  API客户端   │  │   OpenAI SDK        │ │
│  │    前端      │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────────┼────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      接入网关层                              │
│                   Nginx + 限流 + 负载均衡                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     核心业务层 (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   认证授权   │  │  智能路由   │  │     计费统计        │ │
│  │   API Key   │  │  引擎       │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   日志记录   │  │  上游适配   │  │     监控告警        │ │
│  │             │  │  多供应商   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 使用 Docker Compose (推荐)

```bash
# 克隆仓库
git clone https://github.com/yourusername/llm-weaver.git
cd llm-weaver

# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env

# 启动服务
docker-compose up -d

# 访问管理后台
# http://localhost:8080
# 默认账号: admin@example.com / admin123
```

### 手动安装

#### 后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
vim .env

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload
```

#### 前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

## 📁 项目结构

```
llm-weaver/
├── backend/                    # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── v1/           # API v1版本
│   │   │   │   ├── auth.py   # 认证接口
│   │   │   │   ├── api_keys.py
│   │   │   │   ├── channels.py
│   │   │   │   ├── usage.py
│   │   │   │   └── admin/
│   │   │   └── deps.py       # 依赖注入
│   │   ├── core/             # 核心组件
│   │   │   ├── config.py     # 配置管理
│   │   │   ├── security.py   # 安全相关
│   │   │   └── exceptions.py # 异常处理
│   │   ├── db/               # 数据库
│   │   │   ├── base.py       # ORM基类
│   │   │   ├── session.py    # 数据库会话
│   │   │   └── models/       # 数据模型
│   │   ├── models/           # Pydantic模型
│   │   ├── services/         # 业务逻辑
│   │   │   ├── auth.py
│   │   │   ├── router.py     # 路由引擎
│   │   │   ├── billing.py    # 计费服务
│   │   │   └── providers/    # 供应商适配器
│   │   ├── utils/            # 工具函数
│   │   └── main.py           # 应用入口
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 测试代码
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # 前端应用 (Vue3)
│   ├── src/
│   │   ├── api/              # API请求
│   │   ├── components/       # 组件
│   │   ├── views/            # 页面
│   │   ├── router/           # 路由
│   │   ├── stores/           # Pinia状态管理
│   │   └── utils/            # 工具函数
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── nginx/                      # Nginx配置
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL连接URL | `postgresql://user:pass@db:5432/llm_weaver` |
| `REDIS_URL` | Redis连接URL | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT密钥 | 随机生成 |
| `ENCRYPTION_KEY` | 数据加密密钥 | 随机生成 |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 支持的供应商

| 供应商 | 类型标识 | 状态 |
|--------|----------|------|
| OpenAI | `openai` | ✅ 已支持 |
| Anthropic | `anthropic` | ✅ 已支持 |
| Google Gemini | `gemini` | ✅ 已支持 |
| Azure OpenAI | `azure` | ✅ 已支持 |
| Mistral AI | `mistral` | ✅ 已支持 |
| Cohere | `cohere` | ✅ 已支持 |
| Ollama (本地) | `ollama` | ✅ 已支持 |
| vLLM (本地) | `vllm` | ✅ 已支持 |
| 智谱AI | `zhipu` | ✅ 已支持 |
| 文心一言 | `wenxin` | ✅ 已支持 |
| 通义千问 | `qwen` | ✅ 已支持 |
| 自定义 | `custom` | ✅ 已支持 |

## 📖 API 文档

### Swagger UI

启动服务后访问：
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI Schema**: http://localhost:8000/api/v1/openapi.json

### 快速使用示例

#### 1. 用户登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'
```

**响应示例：**
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 604800,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

#### 2. 创建 API Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Production Key",
    "budget_limit": 100.00,
    "rate_limit": 60
  }'
```

**响应示例：**
```json
{
  "code": 201,
  "message": "API Key创建成功",
  "data": {
    "id": 1,
    "key": "sk-llmweaver-abc123xyz789...",
    "name": "My Production Key",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

**⚠️ 注意：API Key 只在创建时返回一次，请妥善保存！**

#### 3. 创建渠道

```bash
curl -X POST http://localhost:8000/api/v1/channels \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI Production",
    "type": "openai",
    "config": {
      "api_key": "sk-openai-your-key-here",
      "api_base": "https://api.openai.com"
    },
    "models": [
      {"model_id": "gpt-4", "mapped_model": "gpt-4"},
      {"model_id": "gpt-3.5-turbo", "mapped_model": "gpt-3.5-turbo"}
    ]
  }'
```

#### 4. 调用 OpenAI 兼容接口

```bash
# 查看可用模型
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer <api_key>"

# 聊天完成
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "temperature": 0.7
  }'
```

**Python 示例：**
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-llmweaver-your-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "你好！"}
    ]
)
print(response.choices[0].message.content)
```

### 详细文档

- [架构设计文档](docs/ARCHITECTURE.md)
- [数据库设计文档](docs/DATABASE_DESIGN.md)
- [API接口规范](docs/API_SPECIFICATION.md)
- [部署指南](docs/DEPLOYMENT.md)
- [开发指南](docs/DEVELOPMENT.md)

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Element Plus](https://element-plus.org/)

---

⭐ 如果这个项目对您有帮助，请给个 Star 支持一下！