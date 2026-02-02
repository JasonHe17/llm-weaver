# AGENTS.md - Coding Guidelines for LLM Weaver

## Project Overview

LLM Weaver is an LLM API gateway service with:
- **Backend**: Python 3.11+ with FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: Vue 3 + TypeScript + Vite + Element Plus
- **Architecture**: Layered (API → Service → Data Access)

## Build & Development Commands

### Backend (Python)

```bash
cd backend/

# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head                    # Run all migrations
alembic revision --autogenerate -m "msg" # Create new migration
alembic downgrade -1                    # Rollback one migration

# Code quality (run before committing)
black app/                              # Format code
flake8 app/                             # Lint check
mypy app/                               # Type check
isort app/                              # Sort imports

# Testing
pytest                                  # Run all tests
pytest tests/unit/                      # Run unit tests only
pytest tests/integration/               # Run integration tests
pytest -k test_name                     # Run specific test by name
pytest tests/unit/test_services/test_auth.py::test_login  # Run single test
pytest --cov=app --cov-report=html      # Run with coverage

# Pre-commit (runs all checks)
pre-commit run --all-files
```

### Frontend (Vue/TypeScript)

```bash
cd frontend/

# Development
npm install
npm run dev                             # Start dev server at localhost:5173

# Build
npm run build                           # Production build
npm run preview                         # Preview production build

# Code quality
npm run lint                            # ESLint check and fix
npm run format                          # Prettier format src/

# Type checking (via build script)
npm run build                           # vue-tsc runs before vite build
```

## Code Style Guidelines

### Python (Backend)

#### Imports
- Use `isort` for import sorting (already configured)
- Order: stdlib → third-party → local
- Use absolute imports for project modules
- Use `TYPE_CHECKING` for circular imports

```python
from typing import List, Optional, TYPE_CHECKING
from fastapi import APIRouter
from sqlalchemy import String, select

from app.core.config import settings
from app.db.base import Base

if TYPE_CHECKING:
    from .api_key import APIKey
```

#### Type Annotations
- **Required**: All function parameters and return types must be annotated
- Use `Optional[T]` for nullable values
- Use Pydantic models for request/response validation
- SQLAlchemy 2.0+: Use `Mapped[T]` for ORM columns

```python
async def get_user(
    user_id: int,
    include_deleted: bool = False
) -> Optional[User]:
    """Get user by ID."""
    pass
```

#### Naming Conventions
- `snake_case` for functions, variables, file names
- `PascalCase` for classes, Pydantic models
- `UPPER_CASE` for constants and settings
- `async def` prefix for async functions
- Private functions prefixed with `_`

#### Docstrings
Use Google-style docstrings:

```python
def function(param: str) -> int:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        BusinessError: When something fails
    """
```

#### Error Handling
- Raise custom `BusinessError` subclasses, not generic exceptions
- Use exception handlers in `main.py` for consistent error responses
- Log exceptions with context using structlog

```python
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import logger

if not user:
    raise NotFoundError(f"User {user_id} not found")

logger.error("Operation failed", user_id=user_id, exc_info=True)
```

#### SQLAlchemy Models
- Inherit from `Base` and `BaseModelMixin`
- Use `Mapped[T]` with `mapped_column()`
- Use `func.now()` for timestamps
- Define relationships with `lazy="selectin"` for eager loading

```python
class User(Base, BaseModelMixin):
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
```

### TypeScript/Vue (Frontend)

#### Component Structure
```vue
<script setup lang="ts">
// Imports first
import { ref, onMounted } from 'vue'
import type { User } from '@/types'

// Props and emits
const props = defineProps<{ userId: number }>()
const emit = defineEmits<{ (e: 'update', user: User): void }>()

// Reactive state
const users = ref<User[]>([])
const loading = ref(false)

// Methods
async function loadUsers() {
  loading.value = true
  try {
    users.value = await fetchUsers()
  } finally {
    loading.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <div class="user-list">
    <el-table :data="users" v-loading="loading">
      <el-table-column prop="name" label="Name" />
    </el-table>
  </div>
</template>

<style scoped>
.user-list { padding: 20px; }
</style>
```

#### Naming
- `camelCase` for variables, functions
- `PascalCase` for components, interfaces, types
- `SCREAMING_SNAKE_CASE` for constants
- Vue components: Multi-word names (e.g., `UserList.vue`)

## Project Structure

```
backend/
├── app/
│   ├── api/              # API layer - HTTP handlers
│   │   ├── v1/           # API version 1
│   │   └── router.py     # Route aggregation
│   ├── core/             # Core components
│   │   ├── config.py     # Settings (Pydantic)
│   │   ├── exceptions.py # Custom exceptions
│   │   ├── logging.py    # Logging setup
│   │   └── security.py   # Auth/security
│   ├── db/               # Database layer
│   │   ├── base.py       # SQLAlchemy base classes
│   │   ├── models/       # ORM models
│   │   └── session.py    # DB session management
│   ├── models/           # Pydantic models (schemas)
│   ├── services/         # Business logic
│   └── main.py           # FastAPI app entry
├── alembic/              # DB migrations
└── tests/                # Test files

frontend/
├── src/
│   ├── api/              # API client functions
│   ├── components/       # Vue components
│   ├── views/            # Page components
│   ├── router/           # Vue Router config
│   ├── stores/           # Pinia stores
│   ├── utils/            # Utility functions
│   └── types/            # TypeScript types
└── package.json
```

## Common Patterns

### API Endpoint Pattern
```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users."""
    service = UserService(db)
    return await service.list_users()
```

### Service Layer Pattern
```python
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

### Custom Exceptions
Available in `app.core.exceptions`:
- `BusinessError` - Base exception (code=400)
- `AuthenticationError` - 401
- `AuthorizationError` - 403
- `NotFoundError` - 404
- `RateLimitError` - 429
- `ValidationError` - 400
- `UpstreamError` - 502

## Git Commit Convention

Format: `<type>(<scope>): <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Build/tooling changes

Example: `feat(api): add batch delete for API keys`

## Pre-commit Checklist

Before committing, always run:

```bash
# Backend
black app/ && flake8 app/ && mypy app/

# Frontend  
npm run lint

# Tests
pytest -x                          # Run tests, stop on first failure
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `SECRET_KEY` - JWT signing key
- `ENCRYPTION_KEY` - Data encryption (32 chars)
