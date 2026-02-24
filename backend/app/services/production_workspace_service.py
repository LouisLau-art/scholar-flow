from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException

from app.core.journal_scope import ensure_manuscript_scope_access
from app.core.role_matrix import ADMIN_ROLE
from app.lib.api_client import supabase_admin
from app.models.manuscript import ManuscriptStatus, normalize_status
from app.models.production_workspace import (
    CreateProductionCycleRequest,
    SubmitProofreadingRequest,
    UpdateProductionCycleEditorsRequest,
)
from app.services.notification_service import NotificationService
from app.services.production_workspace_service_workflow import ProductionWorkspaceWorkflowMixin
from app.services.production_workspace_service_publish_gate import ProductionWorkspacePublishGateMixin


POST_ACCEPTANCE_ALLOWED = {
    ManuscriptStatus.APPROVED.value,
    ManuscriptStatus.LAYOUT.value,
    ManuscriptStatus.ENGLISH_EDITING.value,
    ManuscriptStatus.PROOFREADING.value,
}

ACTIVE_CYCLE_STATUSES = {
    "draft",
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
    "in_layout_revision",
}

AUTHOR_CONTEXT_VISIBLE_STATUSES = {
    "awaiting_author",
    "author_corrections_submitted",
    "author_confirmed",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _to_utc_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _is_truthy_env(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
    }


def _is_table_missing_error(error: Exception, table_name: str) -> bool:
    text = str(error).lower()
    return table_name.lower() in text and "does not exist" in text


def _is_missing_column_error(error: Exception, column_name: str) -> bool:
    text = str(error).lower()
    return column_name.lower() in text and ("column" in text or "schema cache" in text)


def _safe_filename(filename: str) -> str:
    return str(filename or "proof.pdf").replace("/", "_").replace("\\", "_")


class ProductionWorkspaceService(ProductionWorkspaceWorkflowMixin, ProductionWorkspacePublishGateMixin):
    """
    Feature 042: 录用后生产协作工作间。

    中文注释:
    - 管理 production cycle 生命周期。
    - 处理作者校对提交（confirm/corrections）。
    - 提供发布前核准门禁数据。
    """

    def __init__(self) -> None:
        self.client = supabase_admin
        self.notification = NotificationService()

    def _roles(self, profile_roles: list[str] | None) -> set[str]:
        return {str(r).strip().lower() for r in (profile_roles or []) if str(r).strip()}

    def _normalize_uuid_list(self, raw: Any) -> list[str]:
        """
        中文注释：
        - Supabase REST 返回 uuid[] 时可能是 list[str] / list[UUID]；
        - 这里统一成去重后的 string 列表，便于权限判断与序列化。
        """
        if raw is None:
            return []
        if isinstance(raw, (str, bytes)):
            value = str(raw).strip()
            return [value] if value else []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            s = str(item or "").strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

    def _get_profile_roles(self, user_id: str) -> set[str] | None:
        """
        返回 user_profiles.roles 的归一化集合；不存在则返回 None。
        """
        uid = str(user_id or "").strip()
        if not uid:
            return None
        try:
            resp = self.client.table("user_profiles").select("id,roles").eq("id", uid).single().execute()
            row = getattr(resp, "data", None) or None
        except Exception:
            return None
        if not row:
            return None
        return self._roles(row.get("roles") or [])

    def _ensure_bucket(self, bucket: str, *, public: bool = False) -> None:
        storage = getattr(self.client, "storage", None)
        if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
            return
        try:
            storage.get_bucket(bucket)
        except Exception:
            try:
                storage.create_bucket(bucket, options={"public": bool(public)})
            except Exception:
                return

    def _signed_url(self, bucket: str, path: str, expires_in: int = 60 * 10) -> str | None:
        p = str(path or "").strip()
        if not p:
            return None
        try:
            signed = self.client.storage.from_(bucket).create_signed_url(p, expires_in)
            return (signed or {}).get("signedUrl") or (signed or {}).get("signedURL")
        except Exception:
            return None

    def _get_manuscript(self, manuscript_id: str) -> dict[str, Any]:
        try:
            try:
                resp = (
                    self.client.table("manuscripts")
                    .select(
                        "id,title,status,author_id,editor_id,owner_id,assistant_editor_id,file_path,final_pdf_path,updated_at"
                    )
                    .eq("id", manuscript_id)
                    .single()
                    .execute()
                )
            except Exception as first_err:
                if _is_missing_column_error(first_err, "final_pdf_path"):
                    resp = (
                        self.client.table("manuscripts")
                        .select(
                            "id,title,status,author_id,editor_id,owner_id,assistant_editor_id,file_path,updated_at"
                        )
                        .eq("id", manuscript_id)
                        .single()
                        .execute()
                    )
                else:
                    raise
        except Exception as e:
            raise HTTPException(status_code=404, detail="Manuscript not found") from e

        row = getattr(resp, "data", None) or None
        if not row:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return row

    def _ensure_editor_access(
        self,
        *,
        manuscript: dict[str, Any],
        user_id: str,
        roles: set[str],
        cycle: dict[str, Any] | None = None,
        purpose: Literal["read", "write"] = "read",
    ) -> None:
        # Admin 永远放行；其余角色按“期刊 scope / 分配”组合判定。
        if ADMIN_ROLE in roles:
            return

        uid = str(user_id or "").strip()
        manuscript_id = str(manuscript.get("id") or "").strip()

        # --- 显式稿件归属（read only） ---
        # 中文注释:
        # - UAT/开发阶段 user_profiles 可能缺失 journal scope 或存在历史脏数据；
        # - 若稿件已明确绑定到 editor_id / owner_id，
        #   则对应角色应至少具备只读访问（避免生产阶段页面 403 导致流程中断）。
        if purpose == "read":
            assigned_editor_id = str(manuscript.get("editor_id") or "").strip()
            if assigned_editor_id and assigned_editor_id == uid and "managing_editor" in roles:
                return

            assigned_owner_id = str(manuscript.get("owner_id") or "").strip()
            if assigned_owner_id and assigned_owner_id == uid and "owner" in roles:
                return

        # 中文注释:
        # - 一个用户可能同时拥有多个角色（例如 assistant_editor + managing_editor）。
        # - 访问控制应按“任一角色满足即可放行”，避免因为缺少 journal scope 把已被分配的 AE 挡掉。
        # - 但“写操作”必须严格按角色语义执行，避免 ME/EIC 缺 scope 时被 AE 分配兜底放行造成越权。

        # 1) Production Editor: 仅允许访问“分配给自己”的 production cycle（layout_editor_id）。
        #    说明：write/read 都允许，但必须基于 cycle 的真实分配关系。
        if "production_editor" in roles and cycle is not None:
            layout_editor_id = str(cycle.get("layout_editor_id") or "").strip()
            collaborators = set(self._normalize_uuid_list(cycle.get("collaborator_editor_ids")))
            if (layout_editor_id and layout_editor_id == uid) or (uid and uid in collaborators):
                return

        # 2) 写操作：ME/EIC 必须通过 journal scope；其余角色一律不允许写入 production。
        if purpose == "write":
            if roles.intersection({"managing_editor", "editor_in_chief"}):
                ensure_manuscript_scope_access(
                    manuscript_id=manuscript_id,
                    user_id=uid,
                    roles=list(roles),
                    allow_admin_bypass=True,
                )
                return
            raise HTTPException(status_code=403, detail="Forbidden")

        # 3) 读操作：ME/EIC 尝试按 journal scope 放行；失败时允许 AE 以“分配稿件”兜底读取。
        if roles.intersection({"managing_editor", "editor_in_chief"}):
            try:
                ensure_manuscript_scope_access(
                    manuscript_id=manuscript_id,
                    user_id=uid,
                    roles=list(roles),
                    allow_admin_bypass=True,
                )
                return
            except HTTPException:
                pass

        # 4) Assistant Editor:
        #    录用后生产阶段不再由 AE 持续跟进，避免“accepted 后 AE 仍可进入 production”。
        if "assistant_editor" in roles:
            raise HTTPException(status_code=403, detail="Forbidden")

        raise HTTPException(status_code=403, detail="Forbidden")

    def _ensure_author_or_internal_access(
        self,
        *,
        manuscript: dict[str, Any],
        cycle: dict[str, Any],
        user_id: str,
        roles: set[str],
    ) -> bool:
        if roles.intersection({"admin", "managing_editor", "editor_in_chief"}):
            return True

        proofreader_id = str(cycle.get("proofreader_author_id") or "").strip()
        if proofreader_id and proofreader_id == str(user_id):
            return False
        if str(manuscript.get("author_id") or "").strip() == str(user_id):
            return False
        raise HTTPException(status_code=403, detail="Forbidden")

    def _get_cycles(self, manuscript_id: str) -> list[dict[str, Any]]:
        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,collaborator_editor_ids,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .order("cycle_no", desc=True)
                .execute()
            )
            return getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            raise

    def _get_cycle(self, *, manuscript_id: str, cycle_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,collaborator_editor_ids,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .eq("id", cycle_id)
                .single()
                .execute()
            )
            row = getattr(resp, "data", None) or None
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_cycles table missing",
                ) from e
            raise HTTPException(status_code=404, detail="Production cycle not found") from e

        if not row:
            raise HTTPException(status_code=404, detail="Production cycle not found")
        return row

    def _get_latest_response(self, cycle_id: str) -> dict[str, Any] | None:
        try:
            resp = (
                self.client.table("production_proofreading_responses")
                .select("id,cycle_id,manuscript_id,author_id,decision,summary,submitted_at,is_late,created_at")
                .eq("cycle_id", cycle_id)
                .order("submitted_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_proofreading_responses"):
                raise HTTPException(
                    status_code=500,
                    detail="DB not migrated: production_proofreading_responses table missing",
                ) from e
            raise

        if not rows:
            return None

        row = rows[0]
        if str(row.get("decision") or "") == "submit_corrections":
            try:
                c = (
                    self.client.table("production_correction_items")
                    .select("id,line_ref,original_text,suggested_text,reason,sort_order")
                    .eq("response_id", row.get("id"))
                    .order("sort_order", desc=False)
                    .execute()
                )
                row["corrections"] = getattr(c, "data", None) or []
            except Exception:
                row["corrections"] = []
        else:
            row["corrections"] = []
        return row

    def _is_response_current_for_cycle(self, *, cycle: dict[str, Any], response: dict[str, Any] | None) -> bool:
        """
        判断 response 是否属于“当前可提交的这版清样”。

        关键规则：
        - awaiting_author 下，若 response 提交时间早于 cycle.updated_at（通常是 PE 二次上传清样时间），
          视为历史响应，不应阻断作者对新清样再次提交。
        """
        if not response:
            return False

        cycle_status = str(cycle.get("status") or "")
        if cycle_status != "awaiting_author":
            return True

        response_ts = _to_utc_datetime(response.get("submitted_at") or response.get("created_at"))
        cycle_updated_ts = _to_utc_datetime(cycle.get("updated_at"))
        if response_ts is None or cycle_updated_ts is None:
            return True
        return response_ts >= cycle_updated_ts

    def _format_cycle(self, row: dict[str, Any], *, include_signed_url: bool) -> dict[str, Any]:
        bucket = str(row.get("galley_bucket") or "").strip()
        path = str(row.get("galley_path") or "").strip()
        return {
            "id": row.get("id"),
            "manuscript_id": row.get("manuscript_id"),
            "cycle_no": row.get("cycle_no"),
            "status": row.get("status"),
            "layout_editor_id": row.get("layout_editor_id"),
            "collaborator_editor_ids": self._normalize_uuid_list(row.get("collaborator_editor_ids")),
            "proofreader_author_id": row.get("proofreader_author_id"),
            "galley_bucket": bucket or None,
            "galley_path": path or None,
            "galley_signed_url": self._signed_url(bucket, path) if include_signed_url and bucket and path else None,
            "version_note": row.get("version_note"),
            "proof_due_at": row.get("proof_due_at"),
            "approved_by": row.get("approved_by"),
            "approved_at": row.get("approved_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "latest_response": self._get_latest_response(str(row.get("id") or "")),
        }

    def _next_cycle_no(self, manuscript_id: str) -> int:
        cycles = self._get_cycles(manuscript_id)
        if not cycles:
            return 1
        try:
            return int(cycles[0].get("cycle_no") or 0) + 1
        except Exception:
            return 1

    def _insert_log(
        self,
        *,
        manuscript_id: str,
        from_status: str | None,
        to_status: str,
        changed_by: str,
        comment: str,
        payload: dict[str, Any],
    ) -> None:
        now = _utc_now_iso()
        base_row = {
            "manuscript_id": manuscript_id,
            "from_status": from_status,
            "to_status": to_status,
            "comment": comment,
            "changed_by": changed_by,
            "created_at": now,
        }
        rows: list[dict[str, Any]] = []

        # 1) 优先写入带 payload 的版本（审计事件完整）。
        row_with_payload = dict(base_row)
        row_with_payload["payload"] = payload
        rows.append(row_with_payload)

        # 2) 兼容：某些云端/老 schema 可能缺 payload 列（写入降级）。
        rows.append(dict(base_row))

        # 3) 兼容：changed_by 外键指向 auth.users，在测试/种子数据下可能不存在。
        #    用 changed_by=None 写入，同时把原值放进 payload 以便追溯。
        row_no_fk = dict(base_row)
        row_no_fk["changed_by"] = None
        row_no_fk["payload"] = {**payload, "changed_by_raw": changed_by}
        rows.append(row_no_fk)

        # 4) 最小兜底：避免所有 insert 都失败导致无审计。
        rows.append(
            {
                "manuscript_id": manuscript_id,
                "from_status": from_status,
                "to_status": to_status,
                "comment": comment,
                "changed_by": None,
                "created_at": now,
            }
        )

        for row in rows:
            try:
                self.client.table("status_transition_logs").insert(row).execute()
                return
            except Exception as e:
                # 缺 payload 列时，尝试去掉 payload 再写一次
                if "payload" in row and _is_missing_column_error(e, "payload"):
                    fallback = dict(row)
                    fallback.pop("payload", None)
                    try:
                        self.client.table("status_transition_logs").insert(fallback).execute()
                        return
                    except Exception:
                        pass
                continue
        return

    def _notify(self, *, user_id: str | None, manuscript_id: str, title: str, content: str, action_url: str) -> None:
        uid = str(user_id or "").strip()
        if not uid:
            return
        self.notification.create_notification(
            user_id=uid,
            manuscript_id=manuscript_id,
            action_url=action_url,
            type="system",
            title=title,
            content=content,
        )

