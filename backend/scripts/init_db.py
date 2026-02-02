"""
数据库初始化脚本
创建初始管理员用户和基础数据
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.models.user import User
from app.db.models.model_def import ModelDef
from app.db.session import async_session_maker, init_db


async def create_default_models(session):
    """创建默认模型定义."""
    models = [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "provider": "OpenAI",
            "channel_type": "openai",
            "capabilities": ["chat", "vision", "function_calling"],
            "context_window": 8192,
            "pricing_input": 0.03,
            "pricing_output": 0.06,
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "provider": "OpenAI",
            "channel_type": "openai",
            "capabilities": ["chat", "vision", "function_calling"],
            "context_window": 128000,
            "pricing_input": 0.01,
            "pricing_output": 0.03,
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "OpenAI",
            "channel_type": "openai",
            "capabilities": ["chat", "function_calling"],
            "context_window": 4096,
            "pricing_input": 0.0005,
            "pricing_output": 0.0015,
        },
        {
            "id": "gpt-3.5-turbo-16k",
            "name": "GPT-3.5 Turbo 16K",
            "provider": "OpenAI",
            "channel_type": "openai",
            "capabilities": ["chat", "function_calling"],
            "context_window": 16384,
            "pricing_input": 0.001,
            "pricing_output": 0.002,
        },
        {
            "id": "claude-3-opus",
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "channel_type": "anthropic",
            "capabilities": ["chat", "vision"],
            "context_window": 200000,
            "pricing_input": 0.015,
            "pricing_output": 0.075,
        },
        {
            "id": "claude-3-sonnet",
            "name": "Claude 3 Sonnet",
            "provider": "Anthropic",
            "channel_type": "anthropic",
            "capabilities": ["chat", "vision"],
            "context_window": 200000,
            "pricing_input": 0.003,
            "pricing_output": 0.015,
        },
        {
            "id": "gemini-pro",
            "name": "Gemini Pro",
            "provider": "Google",
            "channel_type": "gemini",
            "capabilities": ["chat", "vision"],
            "context_window": 32768,
            "pricing_input": 0.0005,
            "pricing_output": 0.0015,
        },
    ]
    
    for model_data in models:
        # 检查是否已存在
        result = await session.execute(
            select(ModelDef).where(ModelDef.id == model_data["id"])
        )
        if not result.scalar_one_or_none():
            model = ModelDef(**model_data, status="active")
            session.add(model)
            print(f"创建模型: {model_data['name']}")
    
    await session.commit()


async def create_admin_user(session, email: str = "admin@example.com", password: str = "admin123"):
    """创建管理员用户."""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    
    if result.scalar_one_or_none():
        print(f"管理员用户已存在: {email}")
        return
    
    admin = User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        status="active",
        is_active=True,
    )
    
    session.add(admin)
    await session.commit()
    
    print(f"创建管理员用户: {email}")
    print(f"初始密码: {password}")
    print("请登录后立即修改密码！")


async def main():
    """主函数."""
    print("初始化数据库...")
    
    # 初始化数据库
    await init_db()
    
    async with async_session_maker() as session:
        # 创建默认模型
        await create_default_models(session)
        
        # 创建管理员用户
        await create_admin_user(session)
        
        print("\n数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
