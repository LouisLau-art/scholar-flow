from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.lib.api_client import supabase_admin
from app.models.internal_task import INTERNAL_TASK_MUTABLE_STATUSES, InternalTaskPriority, InternalTaskStatus
from app.services.internal_collaboration_service import INTERNAL_COLLAB_ROLES


@dataclass
class InternalTaskSchemaMissingError(Exception):
    table: str


def _extract_rows(resp: Any) -> list[dict[str, Any]]:
    return getattr(resp, "data", None) or []


def _parse_datetime(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _missing_table_from_error(error: Exception | str | None) -> str | None:
    text = str(error or "").lower()
    for table in ("internal_tasks", "internal_task_activity_logs", "internal_comments", "internal_comment_mentions"):
        if table in text and "does not exist" in text:
            return table
    return None


def _has_privileged_role(roles: list[str] | None) -> bool:
    role_set = {str(role).strip().lower() for role in (roles or []) if str(role).strip()}
    return bool(role_set.intersection(INTERNAL_COLLAB_ROLES))


class InternalTaskService:
    """
    Feature 045: manuscript internal tasks + activity timeline.
    """

    def __init__(self, *, client: Any = None) -> None:
        self.client = client or supabase_admin

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_profiles_map(self, user_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = sorted({str(uid).strip() for uid in user_ids if str(uid).strip()})
        if not ids:
            return {}
        try:
            resp = self.client.table("user_profiles").select("id,full_name,email,roles").in_("id", ids).execute()
            return {str(row.get("id")): row for row in _extract_rows(resp) if row.get("id")}
        except Exception:
            return {}

    def _ensure_internal_assignee(self, assignee_user_id: str) -> None:
        profiles = self._load_profiles_map([assignee_user_id])
        profile = profiles.get(assignee_user_id)
        if not profile:
            raise HTTPException(status_code=422, detail="assignee_user_id not found")
        roles = profile.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        if not _has_privileged_role([str(role) for role in roles]):
            raise HTTPException(status_code=422, detail="assignee_user_id must be an internal staff member")

    def _safe_due_iso(self, value: datetime | str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        parsed = _parse_datetime(str(value))
        return parsed.isoformat() if parsed else None

    def _compute_is_overdue(self, row: dict[str, Any]) -> bool:
        status = str(row.get("status") or "").strip().lower()
        if status == InternalTaskStatus.DONE.value:
            return False
        due = _parse_datetime(str(row.get("due_at") or ""))
        if not due:
            return False
        return due < datetime.now(timezone.utc)

    def _enrich_tasks(
        self,
        rows: list[dict[str, Any]],
        *,
        actor_user_id: str | None,
        actor_roles: list[str] | None,
    ) -> list[dict[str, Any]]:
        user_ids: set[str] = set()
        for row in rows:
            if row.get("assignee_user_id"):
                user_ids.add(str(row["assignee_user_id"]))
            if row.get("created_by"):
                user_ids.add(str(row["created_by"]))
        profiles_map = self._load_profiles_map(sorted(user_ids))

        privileged = _has_privileged_role(actor_roles)
        for row in rows:
            assignee_id = str(row.get("assignee_user_id") or "")
            creator_id = str(row.get("created_by") or "")
            row["assignee"] = (
                {
                    "id": assignee_id,
                    "full_name": (profiles_map.get(assignee_id) or {}).get("full_name"),
                    "email": (profiles_map.get(assignee_id) or {}).get("email"),
                }
                if assignee_id
                else None
            )
            row["creator"] = (
                {
                    "id": creator_id,
                    "full_name": (profiles_map.get(creator_id) or {}).get("full_name"),
                    "email": (profiles_map.get(creator_id) or {}).get("email"),
                }
                if creator_id
                else None
            )
            row["is_overdue"] = self._compute_is_overdue(row)
            row["can_edit"] = bool(privileged or (actor_user_id and actor_user_id == assignee_id))
        return rows

    def _load_task_or_404(self, manuscript_id: str, task_id: str) -> dict[str, Any]:
        try:
            resp = (
                self.client.table("internal_tasks")
                .select(
                    "id,manuscript_id,title,description,assignee_user_id,status,priority,due_at,created_by,created_at,updated_at,completed_at"
                )
                .eq("id", task_id)
                .eq("manuscript_id", manuscript_id)
                .single()
                .execute()
            )
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise HTTPException(status_code=404, detail="Task not found") from e

        row = getattr(resp, "data", None) or None
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return row

    def _insert_activity(
        self,
        *,
        task_id: str,
        manuscript_id: str,
        action: str,
        actor_user_id: str,
        before_payload: dict[str, Any] | None,
        after_payload: dict[str, Any] | None,
    ) -> None:
        payload = {
            "task_id": task_id,
            "manuscript_id": manuscript_id,
            "action": action,
            "actor_user_id": actor_user_id,
            "before_payload": before_payload,
            "after_payload": after_payload,
            "created_at": self._now(),
        }
        try:
            self.client.table("internal_task_activity_logs").insert(payload).execute()
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise

    def create_task(
        self,
        *,
        manuscript_id: str,
        actor_user_id: str,
        actor_roles: list[str] | None,
        title: str,
        description: str | None,
        assignee_user_id: str,
        due_at: datetime,
        status: InternalTaskStatus = InternalTaskStatus.TODO,
        priority: InternalTaskPriority = InternalTaskPriority.MEDIUM,
    ) -> dict[str, Any]:
        title_clean = (title or "").strip()
        if not title_clean:
            raise HTTPException(status_code=422, detail="title is required")
        if len(title_clean) > 200:
            raise HTTPException(status_code=422, detail="title too long (max 200)")

        if not _has_privileged_role(actor_roles):
            raise HTTPException(status_code=403, detail="Only internal editors can create tasks")

        self._ensure_internal_assignee(assignee_user_id)

        now = self._now()
        due_iso = self._safe_due_iso(due_at)
        if not due_iso:
            raise HTTPException(status_code=422, detail="due_at is required")

        status_value = status.value if isinstance(status, InternalTaskStatus) else str(status)
        priority_value = priority.value if isinstance(priority, InternalTaskPriority) else str(priority)

        payload: dict[str, Any] = {
            "manuscript_id": manuscript_id,
            "title": title_clean,
            "description": (description or "").strip() or None,
            "assignee_user_id": assignee_user_id,
            "status": status_value,
            "priority": priority_value,
            "due_at": due_iso,
            "created_by": actor_user_id,
            "created_at": now,
            "updated_at": now,
            "completed_at": now if status_value == InternalTaskStatus.DONE.value else None,
        }

        try:
            resp = self.client.table("internal_tasks").insert(payload).execute()
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise

        row = (_extract_rows(resp) or [None])[0]
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create task")

        self._insert_activity(
            task_id=str(row.get("id")),
            manuscript_id=manuscript_id,
            action="task_created",
            actor_user_id=actor_user_id,
            before_payload=None,
            after_payload={
                "status": row.get("status"),
                "assignee_user_id": row.get("assignee_user_id"),
                "due_at": row.get("due_at"),
                "priority": row.get("priority"),
                "title": row.get("title"),
            },
        )

        return self._enrich_tasks([row], actor_user_id=actor_user_id, actor_roles=actor_roles)[0]

    def list_tasks(
        self,
        *,
        manuscript_id: str,
        actor_user_id: str,
        actor_roles: list[str] | None,
        status: InternalTaskStatus | None = None,
        overdue_only: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            query = (
                self.client.table("internal_tasks")
                .select(
                    "id,manuscript_id,title,description,assignee_user_id,status,priority,due_at,created_by,created_at,updated_at,completed_at"
                )
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=True)
            )
            if status:
                status_value = status.value if isinstance(status, InternalTaskStatus) else str(status)
                query = query.eq("status", status_value)
            resp = query.execute()
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise

        rows = _extract_rows(resp)
        enriched = self._enrich_tasks(rows, actor_user_id=actor_user_id, actor_roles=actor_roles)
        if overdue_only:
            enriched = [row for row in enriched if bool(row.get("is_overdue"))]
        return enriched

    def update_task(
        self,
        *,
        manuscript_id: str,
        task_id: str,
        actor_user_id: str,
        actor_roles: list[str] | None,
        title: str | None = None,
        description: str | None = None,
        assignee_user_id: str | None = None,
        status: InternalTaskStatus | None = None,
        priority: InternalTaskPriority | None = None,
        due_at: datetime | None = None,
    ) -> dict[str, Any]:
        current = self._load_task_or_404(manuscript_id, task_id)

        privileged = _has_privileged_role(actor_roles)
        assignee_matches = actor_user_id == str(current.get("assignee_user_id") or "")
        if not privileged and not assignee_matches:
            raise HTTPException(status_code=403, detail="Only assignee or internal editor can update task")

        assignee_only_changes = {
            "title": title,
            "description": description,
            "assignee_user_id": assignee_user_id,
            "priority": priority,
            "due_at": due_at,
        }
        if not privileged and any(value is not None for value in assignee_only_changes.values()):
            raise HTTPException(status_code=403, detail="Only internal editor can update task metadata")

        patch: dict[str, Any] = {}
        before_snapshot: dict[str, Any] = {
            "status": current.get("status"),
            "assignee_user_id": current.get("assignee_user_id"),
            "due_at": current.get("due_at"),
            "priority": current.get("priority"),
            "title": current.get("title"),
            "description": current.get("description"),
        }

        if title is not None:
            title_clean = title.strip()
            if not title_clean:
                raise HTTPException(status_code=422, detail="title cannot be empty")
            if len(title_clean) > 200:
                raise HTTPException(status_code=422, detail="title too long (max 200)")
            if title_clean != str(current.get("title") or ""):
                patch["title"] = title_clean

        if description is not None:
            desc_clean = description.strip() or None
            if desc_clean != current.get("description"):
                patch["description"] = desc_clean

        if assignee_user_id is not None:
            assignee_norm = str(assignee_user_id).strip()
            if not assignee_norm:
                raise HTTPException(status_code=422, detail="assignee_user_id cannot be empty")
            if assignee_norm != str(current.get("assignee_user_id") or ""):
                self._ensure_internal_assignee(assignee_norm)
                patch["assignee_user_id"] = assignee_norm

        if priority is not None:
            priority_value = priority.value if isinstance(priority, InternalTaskPriority) else str(priority)
            try:
                priority_value = InternalTaskPriority(priority_value).value
            except Exception:
                raise HTTPException(status_code=422, detail="invalid priority")
            if priority_value != str(current.get("priority") or ""):
                patch["priority"] = priority_value

        if due_at is not None:
            due_iso = self._safe_due_iso(due_at)
            if not due_iso:
                raise HTTPException(status_code=422, detail="invalid due_at")
            if due_iso != str(current.get("due_at") or ""):
                patch["due_at"] = due_iso

        if status is not None:
            next_status_value = status.value if isinstance(status, InternalTaskStatus) else str(status)
            try:
                next_status = InternalTaskStatus(next_status_value)
            except Exception:
                raise HTTPException(status_code=422, detail="invalid status")

            current_status = InternalTaskStatus(str(current.get("status") or InternalTaskStatus.TODO.value))
            if next_status != current_status:
                allowed = INTERNAL_TASK_MUTABLE_STATUSES.get(current_status, set())
                if next_status not in allowed:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Invalid task status transition: {current_status.value} -> {next_status.value}",
                    )
                patch["status"] = next_status.value
                patch["completed_at"] = self._now() if next_status == InternalTaskStatus.DONE else None

        if not patch:
            return self._enrich_tasks([current], actor_user_id=actor_user_id, actor_roles=actor_roles)[0]

        patch["updated_at"] = self._now()

        try:
            resp = (
                self.client.table("internal_tasks")
                .update(patch)
                .eq("id", task_id)
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise

        rows = _extract_rows(resp)
        if not rows:
            raise HTTPException(status_code=409, detail="Task update conflict")
        updated = rows[0]

        after_snapshot: dict[str, Any] = {
            "status": updated.get("status"),
            "assignee_user_id": updated.get("assignee_user_id"),
            "due_at": updated.get("due_at"),
            "priority": updated.get("priority"),
            "title": updated.get("title"),
            "description": updated.get("description"),
        }

        actions: list[str] = []
        if before_snapshot["status"] != after_snapshot["status"]:
            actions.append("status_changed")
        if before_snapshot["assignee_user_id"] != after_snapshot["assignee_user_id"]:
            actions.append("assignee_changed")
        if before_snapshot["due_at"] != after_snapshot["due_at"]:
            actions.append("due_at_changed")
        if not actions:
            actions.append("task_updated")

        for action in actions:
            self._insert_activity(
                task_id=task_id,
                manuscript_id=manuscript_id,
                action=action,
                actor_user_id=actor_user_id,
                before_payload=before_snapshot,
                after_payload=after_snapshot,
            )

        return self._enrich_tasks([updated], actor_user_id=actor_user_id, actor_roles=actor_roles)[0]

    def list_activity(
        self,
        *,
        manuscript_id: str,
        task_id: str,
    ) -> list[dict[str, Any]]:
        # 保证 task 属于 manuscript，避免越权读取 activity
        self._load_task_or_404(manuscript_id, task_id)

        try:
            resp = (
                self.client.table("internal_task_activity_logs")
                .select("id,task_id,manuscript_id,action,actor_user_id,before_payload,after_payload,created_at")
                .eq("manuscript_id", manuscript_id)
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as e:
            table = _missing_table_from_error(e)
            if table:
                raise InternalTaskSchemaMissingError(table=table) from e
            raise

        rows = _extract_rows(resp)
        actor_ids = sorted({str(row.get("actor_user_id") or "") for row in rows if row.get("actor_user_id")})
        profiles_map = self._load_profiles_map(actor_ids)
        for row in rows:
            actor_id = str(row.get("actor_user_id") or "")
            row["actor"] = (
                {
                    "id": actor_id,
                    "full_name": (profiles_map.get(actor_id) or {}).get("full_name"),
                    "email": (profiles_map.get(actor_id) or {}).get("email"),
                }
                if actor_id
                else None
            )
        return rows
