from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException
from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.lib.api_client import supabase
from pydantic import BaseModel, Field, model_validator

from app.services.matchmaking_service import MatchmakingService

router = APIRouter(prefix="/user", tags=["User Profile"])


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    institution: Optional[str] = Field(default=None, max_length=200)
    research_interests: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_any_field(self):
        if not ((self.name or "").strip() or (self.institution or "").strip() or (self.research_interests or "").strip()):
            raise ValueError("At least one field must be provided")
        return self


@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    获取当前登录用户的详细资料
    """
    # 中文注释: 角色/昵称等信息来自 public.user_profiles（首次访问自动创建）
    return {
        "success": True,
        "data": {
            "id": current_user["id"],
            "email": current_user["email"],
            "name": profile.get("name") or "Demo User",
            "institution": profile.get("institution") or "Unknown",
            "research_interests": profile.get("research_interests") or "",
            "roles": profile.get("roles") or ["author"],
        }
    }

@router.put("/profile")
async def update_profile(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
    req: ProfileUpdateRequest = Body(...),
):
    """
    更新用户资料（持久化到 public.user_profiles）

    中文注释:
    - 安全：仅允许更新自己的 profile（通过 JWT sub 锁定 id）。
    - Feature 012：当用户具备 reviewer 角色时，保存资料会触发后台索引（生成 reviewer embedding）。
    """
    user_id = current_user["id"]
    updates = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.institution is not None:
        updates["institution"] = req.institution.strip()
    if req.research_interests is not None:
        updates["research_interests"] = req.research_interests.strip()

    try:
        resp = supabase.table("user_profiles").update(updates).eq("id", user_id).execute()
        rows = getattr(resp, "data", None) or []
        if len(rows) == 0:
            # 兼容“未先访问 /profile 触发创建”的情况
            insert_payload = {"id": user_id, "email": current_user.get("email"), **updates}
            resp = supabase.table("user_profiles").insert(insert_payload).execute()
            rows = getattr(resp, "data", None) or [insert_payload]
    except Exception as e:
        print(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

    roles = profile.get("roles") or []
    if "reviewer" in roles:
        background_tasks.add_task(MatchmakingService().index_reviewer, user_id)

    return {"success": True, "data": rows[0] if rows else {"id": user_id, **updates}}

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
