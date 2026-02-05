# 开发指南

## 开发环境搭建

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git

### 后端开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/llm-weaver.git
cd llm-weaver/backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 5. 启动PostgreSQL和Redis (使用Docker)
docker run -d -p 5432:5432 -e POSTGRES_USER=llm_weaver -e POSTGRES_PASSWORD=secret postgres:15
docker run -d -p 6379:6379 redis:7

# 6. 数据库迁移
alembic upgrade head

# 7. 创建初始管理员
python scripts/create_admin.py

# 8. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发环境

```bash
# 进入前端目录
cd llm-weaver/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

## 项目结构说明

### 后端代码组织

```
app/
├── api/           # API层 - 处理HTTP请求/响应
├── core/          # 核心 - 配置、安全、异常
├── db/            # 数据库 - 模型、会话
├── models/        # Pydantic模型 - 数据验证
├── services/      # 业务逻辑 - 核心业务
├── utils/         # 工具函数
└── main.py        # 应用入口
```

### 分层架构

```
API Layer (api/)
    │
    ├── 路由定义
    ├── 参数解析
    └── 响应格式化
    ▼
Service Layer (services/)
    │
    ├── 业务逻辑
    ├── 数据校验
    └── 流程编排
    ▼
Data Access Layer (db/)
    │
    ├── ORM模型
    ├── 数据库查询
    └── 事务管理
```

## 编码规范

### Python 规范

1. **PEP 8** 代码风格
2. **类型注解** 必须添加
3. **Docstring** 使用Google风格

```python
from typing import Optional
from pydantic import BaseModel

class UserService:
    """用户服务类.
    
    提供用户相关的业务逻辑处理.
    
    Attributes:
        db_session: 数据库会话
        cache: 缓存客户端
    """
    
    async def get_user(
        self, 
        user_id: int, 
        include_deleted: bool = False
    ) -> Optional[User]:
        """获取用户信息.
        
        Args:
            user_id: 用户ID
            include_deleted: 是否包含已删除用户
            
        Returns:
            User对象或None
            
        Raises:
            UserNotFoundError: 用户不存在
        """
        pass
```

### 代码检查

```bash
# 格式化代码
black app/

# 检查代码风格
flake8 app/

# 类型检查
mypy app/

# 运行所有检查
make lint
```

### Git 提交规范

```
<type>(<scope>): <subject>

<body>
```

类型 (type):
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式 (不影响代码运行)
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建过程/辅助工具

示例:
```
feat(api): 添加API Key批量删除功能

- 支持批量选择删除
- 添加删除确认对话框
- 优化删除性能
```

## API开发规范

### 路由定义

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

@router.get("", response_model=List[APIKeyOut])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """获取API Key列表."""
    return await service.list_by_user(current_user.id)

@router.post("", response_model=APIKeyCreateOut, status_code=201)
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """创建新的API Key."""
    return await service.create(current_user.id, data)
```

### 错误处理

```python
from fastapi import HTTPException
from app.core.exceptions import BusinessError

@app.exception_handler(BusinessError)
async def business_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )
```

## 数据库开发

### 模型定义

```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 迁移管理

```bash
# 创建迁移
alembic revision --autogenerate -m "Add user table"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看历史
alembic history
```

## 测试

### 测试结构

```
tests/
├── conftest.py          # pytest配置
├── unit/                # 单元测试
│   ├── test_config.py           # 配置模块测试
│   ├── test_exceptions.py       # 异常类测试
│   ├── test_security.py         # 安全功能测试
│   ├── schemas/
│   │   ├── test_common.py       # 通用响应模型测试
│   │   ├── test_user.py         # 用户模型测试
│   │   └── test_auth.py         # 认证模型测试
│   └── services/
│       └── test_model_provider.py  # 模型提供商服务测试
├── integration/         # 集成测试
│   └── test_api/
└── e2e/                 # 端到端测试
    └── test_flows/
```

### 编写测试

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_api_key(async_client: AsyncClient, auth_headers):
    """测试创建API Key."""
    response = await async_client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "budget_limit": 100},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["name"] == "Test Key"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_services/

# 带覆盖率报告
pytest --cov=app --cov-report=html

# 并行运行
pytest -n auto
```

## 前端开发规范

### Vue 3 组件规范

```vue
<script setup lang="ts">
/**
 * API Key列表组件
 * 
 * @description 显示和管理用户的API Keys
 * @author Your Name
 */
import { ref, onMounted } from 'vue'
import type { APIKey } from '@/types'

const props = defineProps<{
  userId: number
}>()

const emit = defineEmits<{
  (e: 'created', key: APIKey): void
}>()

// 响应式数据
const apiKeys = ref<APIKey[]>([])
const loading = ref(false)

// 方法
async function loadApiKeys() {
  loading.value = true
  try {
    apiKeys.value = await fetchApiKeys(props.userId)
  } finally {
    loading.value = false
  }
}

onMounted(loadApiKeys)
</script>

<template>
  <div class="api-key-list">
    <el-table :data="apiKeys" v-loading="loading">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>
  </div>
</template>

<style scoped>
.api-key-list {
  padding: 20px;
}
</style>
```

### 状态管理 (Pinia)

```typescript
// stores/user.ts
import { defineStore } from 'pinia'
import type { User } from '@/types'

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null as User | null,
    isLoggedIn: false
  }),
  
  actions: {
    async login(credentials: LoginForm) {
      const user = await authApi.login(credentials)
      this.currentUser = user
      this.isLoggedIn = true
    },
    
    logout() {
      this.currentUser = null
      this.isLoggedIn = false
    }
  }
})
```

## 调试技巧

### 后端调试

```python
# 使用ipdb调试
import ipdb; ipdb.set_trace()

# 或使用breakpoint() (Python 3.7+)
breakpoint()
```

### 日志调试

```python
from app.core.logging import logger

logger.debug(f"Debug info: {variable}")
logger.info("Operation completed")
logger.warning("Something unusual")
logger.error("Error occurred", exc_info=True)
```

## 性能优化

### 数据库查询优化

```python
from sqlalchemy.orm import joinedload

# 使用预加载避免N+1问题
users = await db.execute(
    select(User).options(joinedload(User.api_keys))
)

# 选择性加载字段
users = await db.execute(
    select(User.id, User.username)
)
```

### 缓存使用

```python
from app.core.cache import cache

@cache.cached(timeout=300)
async def get_model_pricing(model_id: str):
    return await pricing_service.get(model_id)

# 手动缓存
await cache.set(f"user:{user_id}", user_data, expire=3600)
user_data = await cache.get(f"user:{user_id}")
```

## 贡献流程

1. **Fork仓库** 并克隆到本地
2. **创建功能分支**: `git checkout -b feature/my-feature`
3. **编写代码和测试**
4. **运行检查**: `make lint && make test`
5. **提交更改**: `git commit -m "feat: add new feature"`
6. **推送到远程**: `git push origin feature/my-feature`
7. **创建PR** 并描述改动

## 常见问题

### 数据库连接失败

```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres

# 检查连接配置
cat .env | grep DATABASE

# 测试连接
psql postgresql://user:pass@localhost:5432/dbname
```

### 前端API请求失败

1. 检查后端服务是否启动
2. 检查CORS配置
3. 检查代理配置 (`vite.config.ts`)

### 热重载不工作

```bash
# 前端
rm -rf node_modules/.vite
cd frontend && npm run dev

# 后端
# 确保使用 --reload 参数
uvicorn app.main:app --reload
```
