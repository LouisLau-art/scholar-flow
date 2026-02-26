from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.services.production_workspace_service_workflow_common import (
    is_missing_column_error,
    is_truthy_env,
    utc_now_iso,
)
from app.services.production_workspace_service_workflow_cycle_context_queue import (
    ProductionWorkspaceWorkflowCycleContextQueueMixin,
)
from app.services.production_workspace_service_workflow_cycle_writes import (
    ProductionWorkspaceWorkflowCycleWritesMixin,
)


class ProductionWorkspaceWorkflowCycleMixin(
    ProductionWorkspaceWorkflowCycleContextQueueMixin,
    ProductionWorkspaceWorkflowCycleWritesMixin,
):
    def get_galley_signed_url(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        roles = self._roles(profile_roles)

        is_internal = roles.intersection({"admin", "managing_editor", "editor_in_chief", "production_editor"})
        if is_internal:
            self._ensure_editor_access(
                manuscript=manuscript,
                user_id=user_id,
                roles=roles,
                cycle=cycle,
                purpose="read",
            )
        else:
            self._ensure_author_or_internal_access(
                manuscript=manuscript,
                cycle=cycle,
                user_id=user_id,
                roles=roles,
            )

        bucket = str(cycle.get("galley_bucket") or "production-proofs")
        path = str(cycle.get("galley_path") or "")
        if not path:
            raise HTTPException(status_code=404, detail="Galley proof not uploaded")
        signed = self._signed_url(bucket, path)
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign galley URL")
        return signed

    def approve_cycle(
        self,
        *,
        manuscript_id: str,
        cycle_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> dict[str, Any]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        cycle = self._get_cycle(manuscript_id=manuscript_id, cycle_id=cycle_id)
        self._ensure_editor_access(
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
            cycle=cycle,
            purpose="write",
        )
        if str(cycle.get("status") or "") != "author_confirmed":
            raise HTTPException(
                status_code=422,
                detail="Cycle can be approved only after author_confirmed",
            )

        galley_path = str(cycle.get("galley_path") or "").strip()
        if not galley_path:
            raise HTTPException(status_code=422, detail="Cannot approve cycle without galley proof")

        now = utc_now_iso()
        try:
            resp = (
                self.client.table("production_cycles")
                .update(
                    {
                        "status": "approved_for_publish",
                        "approved_by": user_id,
                        "approved_at": now,
                        "updated_at": now,
                    }
                )
                .eq("id", cycle_id)
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            if not rows:
                raise HTTPException(status_code=500, detail="Failed to approve cycle")
            row = rows[0]
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to approve cycle: {exc}") from exc

        try:
            self.client.table("manuscripts").update({"final_pdf_path": galley_path}).eq("id", manuscript_id).execute()
        except Exception as exc:
            if is_missing_column_error(exc, "final_pdf_path"):
                if is_truthy_env("PRODUCTION_GATE_ENABLED", "0"):
                    raise HTTPException(
                        status_code=500,
                        detail="Database schema missing final_pdf_path while PRODUCTION_GATE_ENABLED=1",
                    ) from exc
            else:
                raise

        self._insert_log(
            manuscript_id=manuscript_id,
            from_status="author_confirmed",
            to_status="approved_for_publish",
            changed_by=user_id,
            comment="production cycle approved",
            payload={
                "event_type": "production_approved",
                "cycle_id": cycle_id,
                "galley_path": galley_path,
            },
        )
        self._notify(
            user_id=str(manuscript.get("author_id") or ""),
            manuscript_id=manuscript_id,
            title="Production Approved",
            content=f"Your proofreading cycle was approved for publication: '{manuscript.get('title') or manuscript_id}'.",
            action_url="/dashboard",
        )
        return {
            "cycle_id": cycle_id,
            "status": "approved_for_publish",
            "approved_at": row.get("approved_at") or now,
            "approved_by": str(row.get("approved_by") or user_id),
        }
