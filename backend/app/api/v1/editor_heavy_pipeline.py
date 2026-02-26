from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException


async def get_editor_pipeline_impl(
    *,
    supabase_admin_client: Any,
    extract_data_fn,
    per_stage_limit: int | None = None,
) -> dict[str, Any]:
    """
    获取全站稿件流转状态看板数据。

    中文注释:
    - 仅搬运原有逻辑到独立模块，避免 editor.py 继续膨胀。
    - 业务行为保持不变。
    """
    try:
        # 中文注释: 这里使用 service_role 读取，避免启用 RLS 的云端环境导致 editor 看板空数据。
        db = supabase_admin_client
        pipeline_select_fields = "id,title,status,created_at,updated_at"
        default_limit_raw = str(os.getenv("EDITOR_PIPELINE_STAGE_LIMIT", "80") or "80").strip()
        try:
            default_limit = int(default_limit_raw)
        except Exception:
            default_limit = 80
        stage_limit = max(10, min(int(per_stage_limit or default_limit), 300))

        def _with_limit(query):
            if hasattr(query, "limit"):
                return query.limit(stage_limit)
            return query

        # Pre-check（旧：submitted/pending_quality）
        pending_quality_resp = _with_limit(
            db.table("manuscripts")
            .select(pipeline_select_fields)
            .eq("status", "pre_check")
            .order("created_at", desc=True)
        ).execute()
        pending_quality = extract_data_fn(pending_quality_resp) or []

        # 评审中 (under_review)
        under_review_resp = _with_limit(
            db.table("manuscripts")
            .select(f"{pipeline_select_fields}, review_assignments(count)")
            .eq("status", "under_review")
            .order("created_at", desc=True)
        ).execute()
        under_review_data = extract_data_fn(under_review_resp) or []
        # 中文注释: review_assignments(count) 会按“行数”计数，若历史/并发导致重复指派，会把同一 reviewer 计为 2。
        # 这里改为统计 distinct reviewer_id，保证 UI 中 review_count 与“人数”一致。
        under_review_ids = [str(m.get("id")) for m in under_review_data if m.get("id")]
        reviewers_by_ms: dict[str, set[str]] = {}
        if under_review_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", under_review_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count: {e}")
        under_review = []
        for item in under_review_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms.get(mid, set())) if reviewers_by_ms else 0
            if distinct_count == 0 and "review_assignments" in item:
                # 兜底：若 distinct 查询失败，仍用后端原始 count
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            under_review.append(item)

        # 待决策（decision，旧：pending_decision）
        pending_decision_resp = _with_limit(
            db.table("manuscripts")
            .select(f"{pipeline_select_fields}, review_assignments(count)")
            .eq("status", "decision")
            .order("created_at", desc=True)
        ).execute()
        pending_decision_data = extract_data_fn(pending_decision_resp) or []
        pending_ids = [str(m.get("id")) for m in pending_decision_data if m.get("id")]
        reviewers_by_ms_pending: dict[str, set[str]] = {}
        if pending_ids and hasattr(db.table("review_assignments"), "in_"):
            try:
                ras = (
                    db.table("review_assignments")
                    .select("manuscript_id, reviewer_id")
                    .in_("manuscript_id", pending_ids)
                    .execute()
                )
                for row in (getattr(ras, "data", None) or []):
                    mid = str(row.get("manuscript_id") or "")
                    rid = str(row.get("reviewer_id") or "")
                    if not mid or not rid:
                        continue
                    reviewers_by_ms_pending.setdefault(mid, set()).add(rid)
            except Exception as e:
                print(f"Pipeline reviewer count fallback to row count (pending_decision): {e}")
        pending_decision = []
        for item in pending_decision_data:
            mid = str(item.get("id") or "")
            distinct_count = len(reviewers_by_ms_pending.get(mid, set())) if reviewers_by_ms_pending else 0
            if distinct_count == 0 and "review_assignments" in item:
                ra = item["review_assignments"]
                if isinstance(ra, list) and ra and isinstance(ra[0], dict) and "count" in ra[0]:
                    distinct_count = ra[0].get("count", 0)
                elif isinstance(ra, list):
                    distinct_count = len(ra)

            item["review_count"] = distinct_count
            if "review_assignments" in item:
                del item["review_assignments"]
            pending_decision.append(item)

        # Post-acceptance（approved/layout/english_editing/proofreading）- 需要显示发文前的财务状态
        approved_query = (
            db.table("manuscripts")
            .select(f"{pipeline_select_fields}, invoices(id,amount,status)")
            .order("updated_at", desc=True)
        )
        if hasattr(approved_query, "in_"):
            approved_query = approved_query.in_("status", ["approved", "layout", "english_editing", "proofreading"])
        else:
            # 单元测试 stub client 可能不实现 in_；此时仅返回 approved，避免抛错阻断看板。
            approved_query = approved_query.eq("status", "approved")
        approved_resp = _with_limit(approved_query).execute()
        approved_data = extract_data_fn(approved_resp) or []
        approved = []
        for item in approved_data:
            invoices = item.get("invoices")
            # PostgREST 1:1 关联可能返回 dict（而不是 list）
            if isinstance(invoices, dict):
                inv = invoices
            elif isinstance(invoices, list):
                inv = invoices[0] if invoices else {}
            else:
                inv = {}
            item["invoice_amount"] = inv.get("amount")
            item["invoice_status"] = inv.get("status")
            item["invoice_id"] = inv.get("id")
            if "invoices" in item:
                del item["invoices"]
            approved.append(item)

        # 已发布 (published)
        published_resp = _with_limit(
            db.table("manuscripts")
            .select(pipeline_select_fields)
            .eq("status", "published")
            .order("created_at", desc=True)
        ).execute()
        published = extract_data_fn(published_resp) or []

        # 待处理修订稿 (resubmitted) - 类似待质检，需 Editor 处理
        resubmitted_resp = _with_limit(
            db.table("manuscripts")
            .select(pipeline_select_fields)
            .eq("status", "resubmitted")
            .order("updated_at", desc=True)
        ).execute()
        resubmitted = extract_data_fn(resubmitted_resp) or []

        # 等待作者修订（major/minor revision，旧：revision_requested）- 监控用
        revision_requested = []
        try:
            rr_query = (
                db.table("manuscripts")
                .select(pipeline_select_fields)
                .order("updated_at", desc=True)
            )
            if hasattr(rr_query, "in_"):
                rr_query = rr_query.in_("status", ["major_revision", "minor_revision"])
                revision_requested = extract_data_fn(_with_limit(rr_query).execute()) or []
            else:
                # fallback: 两次 eq 合并（不阻断）
                maj = extract_data_fn(
                    _with_limit(
                        db.table("manuscripts")
                        .select(pipeline_select_fields)
                        .eq("status", "major_revision")
                        .order("updated_at", desc=True)
                    ).execute()
                ) or []
                minor = extract_data_fn(
                    _with_limit(
                        db.table("manuscripts")
                        .select(pipeline_select_fields)
                        .eq("status", "minor_revision")
                        .order("updated_at", desc=True)
                    ).execute()
                ) or []
                revision_requested = (maj or []) + (minor or [])
        except Exception as e:
            print(f"Pipeline revision_requested fallback empty: {e}")

        # 已拒稿 (rejected) - 终态归档
        rejected_resp = _with_limit(
            db.table("manuscripts")
            .select(pipeline_select_fields)
            .eq("status", "rejected")
            .order("updated_at", desc=True)
        ).execute()
        rejected = extract_data_fn(rejected_resp) or []

        return {
            "success": True,
            "data": {
                "pending_quality": pending_quality,
                "resubmitted": resubmitted,
                "under_review": under_review,
                "revision_requested": revision_requested,
                "pending_decision": pending_decision,
                "approved": approved,
                "published": published,
                "rejected": rejected,
            },
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")
