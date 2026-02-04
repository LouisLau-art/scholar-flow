from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth_utils import get_current_user, security
from app.core.roles import get_current_profile
from app.schemas.user import UserProfileUpdate, PasswordUpdate
from app.services.user_service import UserService
from app.services.matchmaking_service import MatchmakingService

router = APIRouter(prefix="/user", tags=["User Profile"])

def get_user_service() -> UserService:
    return UserService()

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    """
    获取当前登录用户的详细资料
    """
    return {
        "success": True,
        "data": {
            "id": current_user["id"],
            "email": current_user["email"],
            "full_name": profile.get("full_name") or "Demo User",
            "affiliation": profile.get("affiliation") or "Unknown",
            "title": profile.get("title"),
            "orcid_id": profile.get("orcid_id"),
            "google_scholar_url": profile.get("google_scholar_url"),
            "avatar_url": profile.get("avatar_url"),
            "research_interests": profile.get("research_interests") or [],
            "roles": profile.get("roles") or ["author"],
        }
    }

@router.put("/profile")
async def update_profile(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    req: UserProfileUpdate = Body(...),
    token_auth: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service),
):
    """
    更新用户资料
    """
    user_id = current_user["id"]
    email = current_user["email"]
    access_token = token_auth.credentials

    try:
        updated_profile = user_service.update_profile(
            user_id=user_id,
            update_data=req,
            access_token=access_token,
            email=email
        )
    except Exception as e:
        print(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    roles = updated_profile.get("roles") or []
    if "reviewer" in roles:
        background_tasks.add_task(MatchmakingService().index_reviewer, user_id)

    return {"success": True, "data": updated_profile}

@router.put("/security/password")
async def change_password(
    current_user: dict = Depends(get_current_user),
    req: PasswordUpdate = Body(...),
    user_service: UserService = Depends(get_user_service),
):
    """
    修改密码
    """
    user_id = current_user["id"]
    try:
        user_service.change_password(user_id=user_id, new_password=req.password)
    except Exception as e:
        print(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")
    
    return {"success": True, "message": "Password updated successfully"}

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
