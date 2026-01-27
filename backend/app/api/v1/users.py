from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.auth_utils import get_current_user
from app.lib.api_client import supabase
from typing import Dict, Any

router = APIRouter(prefix="/user", tags=["User Profile"])

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    获取当前登录用户的详细资料
    """
    # 实际环境需查 auth.users 或 profiles 表
    return {
        "success": True,
        "data": {
            "id": current_user["id"],
            "email": current_user["email"],
            "name": "Louis Lau (Demo)",
            "institution": "University of Science",
            "role": "author"
        }
    }

@router.put("/profile")
async def update_profile(
    current_user: dict = Depends(get_current_user),
    name: str = Body(..., embed=True),
    institution: str = Body(..., embed=True)
):
    """
    更新用户资料 (Mock 实现)
    """
    return {"success": True, "message": "Profile updated successfully"}

@router.get("/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    """
    获取系统推送消息
    """
    return {
        "success": True,
        "data": [
            {"id": 1, "title": "Submission Received", "content": "Your manuscript m-001 has been received.", "date": "2026-01-27"},
            {"id": 2, "title": "Payment Confirmed", "content": "The APC for your latest paper has been verified.", "date": "2026-01-26"}
        ]
    }
