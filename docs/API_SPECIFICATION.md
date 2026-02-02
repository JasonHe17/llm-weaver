# API接口规范文档

## 接口概览

| 类别 | 路径前缀 | 说明 |
|------|----------|------|
| OpenAI兼容接口 | `/v1/*` | 完全兼容OpenAI API |
| 原生接口 | `/api/v1/*` | 平台原生REST API |
| 管理后台接口 | `/api/v1/admin/*` | 管理员专用接口 |
| WebSocket | `/ws/*` | 实时推送 |

## 通用规范

### 认证方式

```
Authorization: Bearer {api_key}
```

或 (OpenAI兼容):

```
Authorization: Bearer {api_key}
```

### 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

### 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权/认证失败 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 502 | 上游服务错误 |
| 503 | 服务不可用 |

---

## OpenAI兼容接口

### 1. 模型列表

```
GET /v1/models
```

**响应**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1687882411,
      "owned_by": "openai"
    }
  ]
}
```

### 2. Chat Completions

```
POST /v1/chat/completions
```

**请求体**:
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 150,
  "stream": false
}
```

**响应 (非流式)**:
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

**流式响应** (`stream: true`):
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",...}

data: {"choices":[{"delta":{"content":"Hello"}}]}

data: [DONE]
```

### 3. Embeddings

```
POST /v1/embeddings
```

**请求体**:
```json
{
  "model": "text-embedding-3-small",
  "input": "The food was delicious and the waiter..."
}
```

### 4. Images (DALL-E)

```
POST /v1/images/generations
```

---

## 原生API接口

### 认证接口

#### 登录
```
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

#### 注册
```
POST /api/v1/auth/register
```

#### 刷新Token
```
POST /api/v1/auth/refresh
```

### API Key管理

#### 列出API Keys
```
GET /api/v1/api-keys
```

**查询参数**:
- `page`: 页码 (默认1)
- `page_size`: 每页数量 (默认20)

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Production Key",
        "key_mask": "sk-...xxxx",
        "status": "active",
        "budget_limit": 1000.00,
        "budget_used": 456.78,
        "created_at": "2024-01-15T08:30:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

#### 创建API Key
```
POST /api/v1/api-keys
```

**请求体**:
```json
{
  "name": "My New Key",
  "budget_limit": 500.00,
  "rate_limit": 100,
  "allowed_models": ["gpt-4", "gpt-3.5-turbo"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "key": "sk-llmweaver-xxxxxxxxx",  // 仅创建时返回完整key
    "name": "My New Key",
    "created_at": "2024-01-15T08:30:00Z"
  }
}
```

#### 更新API Key
```
PUT /api/v1/api-keys/{id}
```

#### 删除API Key
```
DELETE /api/v1/api-keys/{id}
```

### 渠道管理

#### 列出渠道
```
GET /api/v1/channels
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "OpenAI Production",
        "type": "openai",
        "status": "active",
        "weight": 100,
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "created_at": "2024-01-10T10:00:00Z"
      }
    ],
    "total": 3
  }
}
```

#### 创建渠道
```
POST /api/v1/channels
```

**请求体**:
```json
{
  "name": "Azure OpenAI",
  "type": "azure",
  "config": {
    "api_base": "https://xxx.openai.azure.com",
    "api_key": "xxxxxx",
    "api_version": "2024-02-01"
  },
  "models": [
    {
      "model_id": "gpt-4",
      "mapped_model": "gpt-4-1106-preview"
    }
  ],
  "weight": 50
}
```

#### 测试渠道
```
POST /api/v1/channels/{id}/test
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "status": "success",
    "latency_ms": 245,
    "tested_at": "2024-01-15T08:30:00Z"
  }
}
```

### 用量统计

#### 获取用量概览
```
GET /api/v1/usage/summary
```

**查询参数**:
- `start_date`: 开始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)

**响应**:
```json
{
  "code": 200,
  "data": {
    "period": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    },
    "total_requests": 15234,
    "total_tokens": 4528901,
    "total_cost": 125.67,
    "by_model": [
      {
        "model": "gpt-4",
        "requests": 5234,
        "tokens": 2012345,
        "cost": 85.50
      },
      {
        "model": "gpt-3.5-turbo",
        "requests": 10000,
        "tokens": 2516556,
        "cost": 40.17
      }
    ],
    "by_day": [
      {
        "date": "2024-01-15",
        "requests": 892,
        "tokens": 234567,
        "cost": 8.45
      }
    ]
  }
}
```

#### 获取详细日志
```
GET /api/v1/usage/logs
```

**查询参数**:
- `model`: 模型筛选
- `api_key_id`: API Key筛选
- `status`: 状态筛选 (success/error)
- `start_date`, `end_date`: 日期范围
- `page`, `page_size`: 分页

### 模型管理

#### 列出可用模型
```
GET /api/v1/models
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "gpt-4",
        "name": "GPT-4",
        "provider": "OpenAI",
        "capabilities": ["chat", "vision", "function_calling"],
        "context_window": 8192,
        "pricing": {
          "input": 0.03,
          "output": 0.06
        },
        "status": "active"
      }
    ]
  }
}
```

---

## 管理后台接口

### 用户管理

```
GET    /api/v1/admin/users
POST   /api/v1/admin/users
GET    /api/v1/admin/users/{id}
PUT    /api/v1/admin/users/{id}
DELETE /api/v1/admin/users/{id}
```

### 系统渠道管理

```
GET    /api/v1/admin/channels
POST   /api/v1/admin/channels
PUT    /api/v1/admin/channels/{id}
DELETE /api/v1/admin/channels/{id}
```

### 系统设置

```
GET /api/v1/admin/settings
PUT /api/v1/admin/settings
```

### 全局统计

```
GET /api/v1/admin/statistics
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "users": {
      "total": 150,
      "active": 135
    },
    "api_keys": {
      "total": 320,
      "active": 280
    },
    "channels": {
      "total": 15,
      "healthy": 14
    },
    "requests": {
      "today": 45230,
      "yesterday": 38921
    },
    "revenue": {
      "today": 1250.50,
      "this_month": 35678.90
    }
  }
}
```

---

## WebSocket 接口

### 连接地址

```
ws://host/ws/v1/stream
```

**认证**: 通过Query参数或Header传递Token

```
ws://host/ws/v1/stream?token={access_token}
```

### 消息格式

**客户端订阅**:
```json
{
  "action": "subscribe",
  "channel": "usage_updates"
}
```

**服务器推送**:
```json
{
  "channel": "usage_updates",
  "data": {
    "api_key_id": 1,
    "daily_usage": {
      "requests": 100,
      "tokens": 5000,
      "cost": 0.15
    }
  }
}
```

### 支持的频道

| 频道 | 说明 |
|------|------|
| `usage_updates` | 用量实时更新 |
| `system_notifications` | 系统通知 |
| `logs_stream` | 实时日志流 |

---

## 供应商特定接口

### 自定义头部传递

某些供应商需要特定头部，可通过以下方式传递:

```
X-Provider-Header-{Name}: value
```

例如:
```
X-Provider-Header-OpenAI-Organization: org-xxx
```

### 供应商配置参数

| 供应商 | 配置参数 |
|--------|----------|
| OpenAI | `api_key`, `organization` (可选) |
| Azure | `api_base`, `api_key`, `api_version` |
| Anthropic | `api_key`, `api_base` (可选) |
| Google | `api_key`, `project_id` |
| 本地模型 | `api_base`, `custom_headers` |

---

## 流式响应规范

### SSE格式

```
data: {json_object}

data: {json_object}

data: [DONE]
```

### 心跳保持

每隔15秒发送注释行:
```
: ping
```

### 错误处理

流式响应中发生错误:
```
data: {"error": {"message": "Upstream error", "code": 502}}

data: [DONE]
```
