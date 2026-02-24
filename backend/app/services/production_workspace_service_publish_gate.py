from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException


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


class ProductionWorkspacePublishGateMixin:
    def assert_publish_gate_ready(self, *, manuscript_id: str) -> dict[str, Any] | None:
        """
        发布前核准门禁：
        - 严格模式（PRODUCTION_CYCLE_STRICT=1）下，必须存在 approved_for_publish 轮次。
        - 非严格模式下，若没有任何生产轮次则降级放行（兼容历史数据）。
        """
        strict = _is_truthy_env("PRODUCTION_CYCLE_STRICT", "0")

        try:
            resp = (
                self.client.table("production_cycles")
                .select("id,manuscript_id,cycle_no,status,galley_path,approved_at")
                .eq("manuscript_id", manuscript_id)
                .order("cycle_no", desc=True)
                .limit(1)
                .execute()
            )
            rows = getattr(resp, "data", None) or []
        except Exception as e:
            if _is_table_missing_error(e, "production_cycles"):
                return None
            raise HTTPException(status_code=500, detail=f"Failed to validate production cycle gate: {e}") from e

        if not rows:
            if strict:
                raise HTTPException(status_code=403, detail="Production approval required before publish")
            return None

        latest = rows[0]
        if str(latest.get("status") or "") != "approved_for_publish":
            raise HTTPException(status_code=403, detail="Latest production cycle is not approved for publish")
        if not str(latest.get("galley_path") or "").strip():
            raise HTTPException(status_code=403, detail="Approved production cycle is missing galley proof")
        return latest
