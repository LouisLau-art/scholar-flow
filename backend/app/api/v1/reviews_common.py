from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from postgrest.exceptions import APIError

from app.core.journal_scope import ensure_manuscript_scope_access


def get_signed_url_for_manuscripts_bucket(
    *,
    file_path: str,
    supabase_client: Any,
    supabase_admin_client: Any,
    expires_in: int = 60 * 10,
) -> str:
    """
    生成 manuscripts bucket 的 signed URL（优先 service_role）。
    """
    last_err: Exception | None = None
    for client in (supabase_admin_client, supabase_client):
        try:
            signed = client.storage.from_("manuscripts").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def get_signed_url_for_review_attachments_bucket(
    *,
    file_path: str,
    supabase_client: Any,
    supabase_admin_client: Any,
    expires_in: int = 60 * 10,
) -> str:
    """
    生成 review-attachments bucket 的 signed URL（优先 service_role）。
    """
    last_err: Exception | None = None
    for client in (supabase_admin_client, supabase_client):
        try:
            signed = client.storage.from_("review-attachments").create_signed_url(file_path, expires_in)
            url = (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
            if url:
                return str(url)
        except Exception as e:
            last_err = e
            continue
    raise HTTPException(status_code=500, detail=f"Failed to create signed url: {last_err}")


def ensure_review_attachments_bucket_exists(*, supabase_admin_client: Any) -> None:
    """
    确保 review-attachments 桶存在（开发/演示环境兜底）。
    """
    storage = getattr(supabase_admin_client, "storage", None)
    if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
        return

    try:
        storage.get_bucket("review-attachments")
        return
    except Exception:
        pass
    try:
        storage.create_bucket("review-attachments", options={"public": False})
    except Exception as e:
        text = str(e).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            return
        raise


def is_missing_relation_error(err: Exception, *, relation: str) -> bool:
    """判断是否为缺表/Schema cache 未更新错误。"""
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    return (
        "42p01" in text
        or "pgrst205" in text
        or "schema cache" in text
        or f'"{relation.lower()}"' in text
        and "does not exist" in text
    )


def is_foreign_key_user_error(err: Exception, *, constraint: str) -> bool:
    if not isinstance(err, APIError):
        return False
    text = str(err).lower()
    return ("23503" in text or "foreign key" in text) and constraint.lower() in text


def safe_insert_invite_policy_audit(
    *,
    supabase_admin_client: Any,
    manuscript_id: str,
    from_status: str,
    to_status: str,
    changed_by: str | None,
    comment: str | None,
    payload: dict[str, Any],
) -> None:
    """邀请策略相关审计日志（fail-open，不影响主流程）。"""
    base = {
        "manuscript_id": manuscript_id,
        "from_status": from_status,
        "to_status": to_status,
        "comment": comment,
        "changed_by": changed_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    candidates = [dict(base)]
    no_payload = dict(base)
    no_payload.pop("payload", None)
    candidates.append(no_payload)
    if changed_by:
        changed_by_none = dict(base)
        changed_by_none["changed_by"] = None
        changed_by_none["payload"] = {**payload, "changed_by_raw": changed_by}
        candidates.append(changed_by_none)
        changed_by_none_no_payload = dict(changed_by_none)
        changed_by_none_no_payload.pop("payload", None)
        candidates.append(changed_by_none_no_payload)

    for row in candidates:
        try:
            supabase_admin_client.table("status_transition_logs").insert(row).execute()
            return
        except Exception:
            continue


def parse_roles(profile: dict | None) -> list[str]:
    raw = (profile or {}).get("roles") or []
    return [str(r).strip().lower() for r in raw if str(r).strip()]


def ensure_review_management_access(
    *,
    manuscript: dict[str, Any],
    user_id: str,
    roles: set[str],
) -> None:
    """
    审稿人管理权限校验（assign/unassign/list）。
    """
    if "admin" in roles:
        return

    manuscript_id = str(manuscript.get("id") or "").strip()
    if not manuscript_id:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    if "managing_editor" in roles:
        ensure_manuscript_scope_access(
            manuscript_id=manuscript_id,
            user_id=str(user_id),
            roles=roles,
        )
        return

    if "assistant_editor" in roles:
        assigned_ae = str(manuscript.get("assistant_editor_id") or "").strip()
        if assigned_ae != str(user_id).strip():
            raise HTTPException(status_code=403, detail="Forbidden: manuscript not assigned to current assistant editor")
        return

    raise HTTPException(status_code=403, detail="Insufficient role")


def is_admin_email(email: Optional[str]) -> bool:
    if not email:
        return False
    admins = [e.strip().lower() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()]
    return email.strip().lower() in set(admins)
