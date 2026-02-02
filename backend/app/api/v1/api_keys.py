"""
API Key 管理接口
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_api_keys():
    """获取API Key列表."""
    return {"message": "List API keys endpoint - TODO"}


@router.post("")
async def create_api_key():
    """创建新的API Key."""
    return {"message": "Create API key endpoint - TODO"}


@router.delete("/{key_id}")
async def delete_api_key(key_id: int):
    """删除API Key."""
    return {"message": f"Delete API key {key_id} endpoint - TODO"}
