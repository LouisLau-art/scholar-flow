from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.models.production_workspace import SubmitProofreadingRequest
from app.services.production_workspace_service_workflow_common import (
    AUTHOR_CONTEXT_VISIBLE_STATUSES,
    is_missing_column_error,
    is_table_missing_error,
    production_sop_schema_http_error,
    utc_now,
)


class ProductionWorkspaceWorkflowAuthorMixin:
    def get_author_proofreading_context(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)

        try:
            resp = (
                self.client.table("production_cycles")
                .select(
                    "id,manuscript_id,cycle_no,status,layout_editor_id,proofreader_author_id,"
                    "galley_bucket,galley_path,version_note,proof_due_at,approved_by,approved_at,created_at,updated_at"
                )
                .eq("manuscript_id", manuscript_id)
                .in_("status", sorted(AUTHOR_CONTEXT_VISIBLE_STATUSES))
                .order("cycle_no", desc=True)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if is_table_missing_error(e, "production_cycles"):
                raise production_sop_schema_http_error("production_cycles table missing") from e
            raise

        if not rows:
            raise HTTPException(status_code=404, detail="No proofreading task available")

        cycle = rows[0]
        self._ensure_author_or_internal_access(
            manuscript=manuscript,
            cycle=cycle,
            user_id=user_id,
            roles=roles,
        )

        cycle_status = str(cycle.get("status") or "")
        can_act_on_cycle = cycle_status == "awaiting_author"
        cycle_data = self._format_cycle(cycle, include_signed_url=True)
        latest = cycle_data.get("latest_response")
        active_latest = latest if self._is_response_current_for_cycle(cycle=cycle, response=latest) else None
        cycle_data["latest_response"] = active_latest
        read_only = (not can_act_on_cycle) or (active_latest is not None)

        due_raw = cycle.get("proof_due_at")
        due_at: datetime | None = None
        if isinstance(due_raw, datetime):
            due_at = due_raw
        elif isinstance(due_raw, str) and due_raw:
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
            except Exception:
                due_at = None

        if due_at and due_at < utc_now():
            read_only = True

        return {
            "manuscript": {
                "id": manuscript.get("id"),
                "title": manuscript.get("title") or "Untitled",
                "status": manuscript.get("status"),
            },
            "cycle": cycle_data,
            "can_submit": can_act_on_cycle and not read_only,
            "is_read_only": read_only,
        }

    def submit_proofreading(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        request: SubmitProofreadingRequest,
        attachment_content: bytes | None = None,
        attachment_filename: str | None = None,
        attachment_content_type: str | None = None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        roles = self._roles(profile_roles)

        is_internal = self._ensure_author_or_internal_access(
            manuscript=manuscript,
            cycle=cycle,
            user_id=user_id,
            roles=roles,
        )
        if is_internal:
            raise HTTPException(status_code=403, detail="Internal users cannot submit author proofreading")

        if str(cycle.get("status") or "") != "awaiting_author":
            raise HTTPException(status_code=409, detail="Cycle is not awaiting author response")

        existing = self._get_latest_response(str(cycle.get("id") or ""))
        existing_is_current = self._is_response_current_for_cycle(cycle=cycle, response=existing)
        if existing_is_current:
            raise HTTPException(status_code=409, detail="Proofreading response already submitted")

        due_raw = cycle.get("proof_due_at")
        due_at: datetime | None = None
        if isinstance(due_raw, datetime):
            due_at = due_raw
        elif isinstance(due_raw, str) and due_raw:
            try:
                due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
            except Exception:
                due_at = None

        now = utc_now()
        if due_at and now > due_at:
            raise HTTPException(status_code=422, detail="Proofreading deadline has passed")

        decision = str(request.decision)
        new_status = "author_confirmed" if decision == "confirm_clean" else "author_corrections_submitted"

        submitted_at = now.isoformat()
        response_reused = False
        
        attachment_bucket = None
        attachment_path = None
        attachment_file_name_val = None
        
        if attachment_content and attachment_filename:
            from uuid import uuid4
            from app.core.storage_filename import sanitize_storage_filename
            self._ensure_bucket("production-proof-attachments", public=False)
            attachment_bucket = "production-proof-attachments"
            attachment_file_name_val = attachment_filename
            safe_name = sanitize_storage_filename(attachment_filename, default_name="annotated")
            attachment_path = f"production_feedback/{manuscript_id}/{uuid4()}_{safe_name}"
            
            try:
                self.client.storage.from_(attachment_bucket).upload(
                    attachment_path,
                    attachment_content,
                    {"content-type": attachment_content_type or "application/octet-stream"},
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {exc}") from exc
                
            try:
                self.client.table("production_cycle_artifacts").insert({
                    "cycle_id": cycle_id,
                    "manuscript_id": manuscript_id,
                    "artifact_kind": "author_annotated_proof",
                    "storage_bucket": attachment_bucket,
                    "storage_path": attachment_path,
                    "file_name": attachment_file_name_val,
                    "mime_type": attachment_content_type or "application/octet-stream",
                    "uploaded_by": user_id,
                    "metadata": {"source": "author_feedback"}
                }).execute()
            except Exception as exc:
                try:
                    bucket = self.client.storage.from_(attachment_bucket)
                    remover = getattr(bucket, "remove", None)
                    if callable(remover):
                        remover([attachment_path])
                except Exception:
                    pass
                if is_table_missing_error(exc, "production_cycle_artifacts"):
                    raise production_sop_schema_http_error("production_cycle_artifacts table missing") from exc
                if any(
                    is_missing_column_error(exc, column)
                    for column in ("artifact_kind", "storage_bucket", "storage_path", "metadata")
                ):
                    raise production_sop_schema_http_error("production_cycle_artifacts schema missing") from exc
                raise HTTPException(status_code=500, detail=f"Failed to record author attachment artifact: {exc}") from exc
                
        try:
            if existing and not existing_is_current and str(existing.get("id") or "").strip():
                response_reused = True
                response_id = str(existing.get("id") or "").strip()
                update_payload = {
                    "author_id": user_id,
                    "decision": decision,
                    "summary": request.summary,
                    "submitted_at": submitted_at,
                    "is_late": bool(due_at and now > due_at),
                }
                if attachment_path:
                    update_payload["attachment_bucket"] = attachment_bucket
                    update_payload["attachment_path"] = attachment_path
                    update_payload["attachment_file_name"] = attachment_file_name_val
                
                try:
                    resp = (
                        self.client.table("production_proofreading_responses")
                        .update(update_payload)
                        .eq("id", response_id)
                        .eq("cycle_id", cycle_id)
                        .eq("manuscript_id", manuscript_id)
                        .execute()
                    )
                except Exception as e:
                    if is_missing_column_error(e, "attachment_bucket"):
                        raise production_sop_schema_http_error("production_proofreading_responses attachment columns missing") from e
                    else:
                        raise e
                        
                rows = getattr(resp, "data", None) or []
                if not rows:
                    raise HTTPException(status_code=500, detail="Failed to update proofreading response")
                response_row = rows[0]
            else:
                response_payload = {
                    "cycle_id": cycle_id,
                    "manuscript_id": manuscript_id,
                    "author_id": user_id,
                    "decision": decision,
                    "summary": request.summary,
                    "submitted_at": submitted_at,
                    "is_late": bool(due_at and now > due_at),
                    "created_at": submitted_at,
                }
                if attachment_path:
                    response_payload["attachment_bucket"] = attachment_bucket
                    response_payload["attachment_path"] = attachment_path
                    response_payload["attachment_file_name"] = attachment_file_name_val
                    
                try:
                    resp = self.client.table("production_proofreading_responses").insert(response_payload).execute()
                except Exception as e:
                    if is_missing_column_error(e, "attachment_bucket"):
                        raise production_sop_schema_http_error("production_proofreading_responses attachment columns missing") from e
                    else:
                        raise e
                        
                rows = getattr(resp, "data", None) or []
                if not rows:
                    raise HTTPException(status_code=500, detail="Failed to save proofreading response")
                response_row = rows[0]
        except HTTPException:
            raise
        except Exception as e:
            if attachment_path:
                try:
                    bucket = self.client.storage.from_(attachment_bucket)
                    remover = getattr(bucket, "remove", None)
                    if callable(remover):
                        remover([attachment_path])
                except Exception:
                    pass
            if is_table_missing_error(e, "production_proofreading_responses"):
                raise production_sop_schema_http_error("production_proofreading_responses table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to save proofreading response: {e}") from e

        response_id = str(response_row.get("id") or "").strip()
        try:
            if response_id:
                self.client.table("production_correction_items").delete().eq("response_id", response_id).execute()
        except Exception as e:
            if is_table_missing_error(e, "production_correction_items"):
                raise production_sop_schema_http_error("production_correction_items table missing") from e
            if is_missing_column_error(e, "response_id"):
                raise production_sop_schema_http_error("production_correction_items schema missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to reset correction items: {e}") from e

        if decision == "submit_corrections":
            items = []
            for idx, item in enumerate(request.corrections):
                items.append(
                    {
                        "response_id": response_id,
                        "line_ref": item.line_ref,
                        "original_text": item.original_text,
                        "suggested_text": item.suggested_text,
                        "reason": item.reason,
                        "sort_order": idx,
                    }
                )
            try:
                if items:
                    self.client.table("production_correction_items").insert(items).execute()
            except Exception as e:
                if is_table_missing_error(e, "production_correction_items"):
                    raise production_sop_schema_http_error("production_correction_items table missing") from e
                if any(
                    is_missing_column_error(e, column)
                    for column in ("response_id", "line_ref", "original_text", "suggested_text", "reason", "sort_order")
                ):
                    raise production_sop_schema_http_error("production_correction_items schema missing") from e
                raise HTTPException(status_code=500, detail=f"Failed to save correction items: {e}") from e

        try:
            next_assignee_id = (
                str(cycle.get("coordinator_ae_id") or "").strip()
                or str(cycle.get("layout_editor_id") or "").strip()
                or str(cycle.get("current_assignee_id") or "").strip()
                or None
            )
            self.client.table("production_cycles").update(
                {
                    "status": new_status,
                    "stage": "ae_final_review",
                    "current_assignee_id": next_assignee_id,
                    "updated_at": submitted_at,
                }
            ).eq("id", cycle_id).eq("manuscript_id", manuscript_id).execute()
        except Exception as e:
            if any(is_missing_column_error(e, column) for column in ("stage", "current_assignee_id")):
                raise production_sop_schema_http_error("production_cycles SOP columns missing") from e
            else:
                raise HTTPException(status_code=500, detail=f"Failed to update cycle status: {e}") from e

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status="awaiting_author",
            to_status=new_status,
            changed_by=user_id,
            comment="proofreading submitted",
            payload={
                "event_type": "proofreading_submitted",
                "from_stage": "author_proofreading",
                "to_stage": "ae_final_review",
                "cycle_id": cycle_id,
                "decision": decision,
                "response_id": response_row.get("id"),
                "response_reused": response_reused,
                "attachment_path": attachment_path,
            },
        )

        if decision == "submit_corrections":
            recipients: list[str] = []
            layout_id = str(cycle.get("layout_editor_id") or "").strip()
            if layout_id:
                recipients.append(layout_id)
            recipients.extend(self._normalize_uuid_list(cycle.get("collaborator_editor_ids")))
            if not recipients:
                fallback = str(manuscript.get("editor_id") or "").strip()
                if fallback:
                    recipients.append(fallback)
            recipients = list(dict.fromkeys([r for r in recipients if str(r).strip()]))
            for uid in recipients:
                self._notify(
                    user_id=uid,
                    manuscript_id=manuscript_id,
                    title="Proof Corrections Submitted",
                    content=f"Author submitted corrections for manuscript '{manuscript.get('title') or manuscript_id}'.",
                    action_url=f"/editor/production/{manuscript_id}",
                )
        else:
            self._notify(
                user_id=str(manuscript.get("editor_id") or manuscript.get("owner_id") or ""),
                manuscript_id=manuscript_id,
                title="Proofreading Confirmed",
                content=f"Author confirmed galley proof for manuscript '{manuscript.get('title') or manuscript_id}'.",
                action_url=f"/editor/production/{manuscript_id}",
            )

        return {
            "response_id": response_row.get("id"),
            "cycle_id": cycle_id,
            "decision": decision,
            "submitted_at": response_row.get("submitted_at") or submitted_at,
            "attachment_file_name": response_row.get("attachment_file_name"),
        }
