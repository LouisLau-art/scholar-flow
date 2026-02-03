import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import RedirectResponse
from supabase import create_client

from app.core.config import app_config
from app.lib.api_client import supabase_admin


router = APIRouter(prefix="/auth", tags=["Auth"])


def _is_dev_env() -> bool:
    return (os.environ.get("GO_ENV") or "").strip().lower() == "dev"


def _get_frontend_origin() -> str:
    return (os.environ.get("FRONTEND_ORIGIN") or "http://localhost:3000").rstrip("/")


@router.get("/dev-login")
async def dev_login(
    email: str = Query(..., description="登录邮箱（仅 dev 环境可用）"),
    next: str = Query("/dashboard", description="登录后跳转路径"),
):
    """
    开发环境登录后门（仅 GO_ENV=dev 可用）。

    流程：
    1) 后端用 service role 调用 Admin API 生成 magiclink OTP（不会发送邮件）
    2) 后端再用 anon client 调用 verify_otp 换取 session（access/refresh token）
    3) 重定向到前端 /auth/callback，交由前端写入 Supabase session
    """
    if not _is_dev_env():
        # 中文注释: 生产环境必须“像不存在一样”，避免误配置导致可被外部探测。
        raise HTTPException(status_code=404, detail="Not found")

    frontend_origin = _get_frontend_origin()

    try:
        link_res = supabase_admin.auth.admin.generate_link(
            {
                "type": "magiclink",
                "email": email,
                # 这里 redirect_to 只是用于生成 link 的规范性；我们会直接 verify_otp 并重定向前端。
                "options": {"redirect_to": f"{frontend_origin}/auth/callback"},
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate link: {e}")

    props = getattr(link_res, "properties", None)
    if isinstance(props, dict):
        email_otp = props.get("email_otp")
    else:
        email_otp = getattr(props, "email_otp", None)

    if not email_otp:
        raise HTTPException(status_code=400, detail="Missing email_otp from generate_link response")

    anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY") or ""
    if not app_config.supabase_url or not anon_key:
        raise HTTPException(status_code=500, detail="Supabase URL/ANON key not configured")

    try:
        anon_client = create_client(app_config.supabase_url, anon_key)
        auth_res = anon_client.auth.verify_otp({"email": email, "token": email_otp, "type": "magiclink"})
        session = getattr(auth_res, "session", None)
        access_token = getattr(session, "access_token", None) if session else None
        refresh_token = getattr(session, "refresh_token", None) if session else None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify otp: {e}")

    if not access_token or not refresh_token:
        raise HTTPException(status_code=400, detail="Failed to obtain session tokens")

    qs = urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "next": next,
        }
    )
    return RedirectResponse(url=f"{frontend_origin}/auth/callback?{qs}", status_code=302)

