from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException

from app.services.production_workspace_service_workflow_common import (
    is_missing_column_error,
    is_table_missing_error,
    production_sop_schema_http_error,
)


def _is_truthy_env(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
    }


class ProductionWorkspacePublishGateMixin:
    def assert_publish_gate_ready(self, *, manuscript_id: str) -> dict[str, Any] | None:
        """
        发布前核准门禁：
        - 严格模式（PRODUCTION_CYCLE_STRICT=1）下，必须存在 ready_to_publish 轮次。
        - 非严格模式下，若没有任何生产轮次则降级放行（兼容历史数据）。
        """
        strict = _is_truthy_env("PRODUCTION_CYCLE_STRICT", "0")

        try:
            try:
                resp = (
                    self.client.table("production_cycles")
                    .select("id,manuscript_id,cycle_no,status,stage,galley_path,approved_at")
                    .eq("manuscript_id", manuscript_id)
                    .order("cycle_no", desc=True)
                    .limit(1)
                    .execute()
                )
            except Exception as e:
                if is_missing_column_error(e, "stage"):
                    raise production_sop_schema_http_error("production_cycles stage column missing") from e
                if any(is_missing_column_error(e, column) for column in ("approved_at", "galley_path")):
                    raise production_sop_schema_http_error("production_cycles publish gate columns missing") from e
                else:
                    raise
            rows = getattr(resp, "data", None) or []
        except HTTPException:
            raise
        except Exception as e:
            if is_table_missing_error(e, "production_cycles"):
                raise production_sop_schema_http_error("production_cycles table missing") from e
            raise HTTPException(status_code=500, detail=f"Failed to validate production cycle gate: {e}") from e

        if not rows:
            if strict:
                raise HTTPException(status_code=403, detail="Production approval required before publish")
            return None

        latest = rows[0]
        
        from app.services.production_workspace_service import _derive_cycle_stage
        stage = _derive_cycle_stage(status=latest.get("status"), stage=latest.get("stage"))
        
        if stage != "ready_to_publish":
            raise HTTPException(status_code=403, detail="Latest production cycle is not approved for publish")
        if not str(latest.get("galley_path") or "").strip():
            raise HTTPException(status_code=403, detail="Approved production cycle is missing galley proof")
        return latest
