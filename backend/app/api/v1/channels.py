"""
渠道管理接口
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_channels():
    """获取渠道列表."""
    return {"message": "List channels endpoint - TODO"}


@router.post("")
async def create_channel():
    """创建新渠道."""
    return {"message": "Create channel endpoint - TODO"}


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int):
    """删除渠道."""
    return {"message": f"Delete channel {channel_id} endpoint - TODO"}
