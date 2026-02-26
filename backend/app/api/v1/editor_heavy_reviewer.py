from __future__ import annotations

from typing import Any

from fastapi import HTTPException


async def get_available_reviewers_impl(
    *,
    current_user: dict[str, Any],
    supabase_client: Any,
    extract_data_fn,
    page: int = 1,
    page_size: int = 50,
    q: str | None = None,
) -> dict[str, Any]:
    """获取可用的审稿人专家池（搬运原逻辑）。"""
    self_candidate = None
    try:
        try:
            page_num = max(int(page or 1), 1)
        except Exception:
            page_num = 1
        try:
            per_page = max(min(int(page_size or 50), 100), 1)
        except Exception:
            per_page = 50
        offset = (page_num - 1) * per_page
        keyword = q.strip() if isinstance(q, str) else ""

        user_id = current_user.get("id")
        email = current_user.get("email")
        if user_id and email:
            name_part = email.split("@")[0].replace(".", " ").title()
            self_candidate = {
                "id": str(user_id),
                "name": f"{name_part} (You)",
                "email": email,
                "affiliation": "Your Account",
                "expertise": ["AI", "Systems"],
                "review_count": 0,
            }

        reviewers_query = (
            supabase_client.table("user_profiles")
            .select("id, email, roles", count="exact")
            .contains("roles", ["reviewer"])
        )
        if hasattr(reviewers_query, "order"):
            reviewers_query = reviewers_query.order("email", desc=False)
        if hasattr(reviewers_query, "range"):
            reviewers_query = reviewers_query.range(offset, offset + per_page - 1)
        else:
            if hasattr(reviewers_query, "limit"):
                reviewers_query = reviewers_query.limit(per_page)
            if hasattr(reviewers_query, "offset"):
                reviewers_query = reviewers_query.offset(offset)
        if keyword:
            reviewers_query = reviewers_query.ilike("email", f"%{keyword}%")
        reviewers_resp = reviewers_query.execute()
        reviewers = extract_data_fn(reviewers_resp) or []
        count_value = getattr(reviewers_resp, "count", None)
        total_count = count_value if isinstance(count_value, int) else len(reviewers)

        formatted_reviewers = []
        for reviewer in reviewers:
            email = reviewer.get("email") or "reviewer@example.com"
            name_part = email.split("@")[0].replace(".", " ").title()
            formatted_reviewers.append(
                {
                    "id": reviewer["id"],
                    "name": name_part or "Reviewer",
                    "email": email,
                    "affiliation": "Independent Researcher",
                    "expertise": ["AI", "Systems"],
                    "review_count": 0,
                }
            )

        if formatted_reviewers:
            if self_candidate and not any(r["id"] == self_candidate["id"] for r in formatted_reviewers):
                formatted_reviewers.insert(0, self_candidate)
            return {
                "success": True,
                "data": formatted_reviewers,
                "meta": {
                    "page": page_num,
                    "page_size": per_page,
                    "total": total_count,
                    "has_more": (offset + len(reviewers)) < total_count,
                },
            }

        # fallback: demo reviewers for empty dataset
        if self_candidate:
            return {
                "success": True,
                "data": [
                    self_candidate,
                    {
                        "id": "88888888-8888-8888-8888-888888888888",
                        "name": "Dr. Demo Reviewer",
                        "email": "reviewer1@example.com",
                        "affiliation": "Demo Lab",
                        "expertise": ["AI", "NLP"],
                        "review_count": 12,
                    },
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "name": "Prof. Sample Expert",
                        "email": "reviewer2@example.com",
                        "affiliation": "Sample University",
                        "expertise": ["Machine Learning", "Computer Vision"],
                        "review_count": 8,
                    },
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "name": "Dr. Placeholder",
                        "email": "reviewer3@example.com",
                        "affiliation": "Research Institute",
                        "expertise": ["Security", "Blockchain"],
                        "review_count": 5,
                    },
                ],
                "meta": {
                    "page": page_num,
                    "page_size": per_page,
                    "total": 4,
                    "has_more": False,
                },
            }
        return {
            "success": True,
            "data": [
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "name": "Dr. Demo Reviewer",
                    "email": "reviewer1@example.com",
                    "affiliation": "Demo Lab",
                    "expertise": ["AI", "NLP"],
                    "review_count": 12,
                },
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "name": "Prof. Sample Expert",
                    "email": "reviewer2@example.com",
                    "affiliation": "Sample University",
                    "expertise": ["Machine Learning", "Computer Vision"],
                    "review_count": 8,
                },
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "name": "Dr. Placeholder",
                    "email": "reviewer3@example.com",
                    "affiliation": "Research Institute",
                    "expertise": ["Security", "Blockchain"],
                    "review_count": 5,
                },
            ],
            "meta": {
                "page": page_num,
                "page_size": per_page,
                "total": 3,
                "has_more": False,
            },
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        if self_candidate:
            return {"success": True, "data": [self_candidate]}
        return {"success": True, "data": []}


async def search_reviewer_library_impl(
    *,
    query: str,
    page: int,
    page_size: int,
    manuscript_id: str | None,
    profile: dict[str, Any],
    supabase_admin_client: Any,
    reviewer_service_cls,
    review_policy_service_cls,
    normalize_roles_fn,
) -> dict[str, Any]:
    """Reviewer Library 搜索（搬运原逻辑并保留依赖注入）。"""
    try:
        reviewer_service = reviewer_service_cls()
        rows: list[dict[str, Any]]
        pagination: dict[str, Any]
        if hasattr(reviewer_service, "search_page"):
            page_result = reviewer_service.search_page(query=query, page=page, page_size=page_size)
            rows = list(page_result.get("items") or [])
            pagination = {
                "page": int(page_result.get("page") or page),
                "page_size": int(page_result.get("page_size") or page_size),
                "returned": len(rows),
                "has_more": bool(page_result.get("has_more")),
            }
        else:
            # 兼容旧测试 stub（仅实现 search(query, limit)）。
            rows = reviewer_service.search(query=query, limit=page_size)
            pagination = {
                "page": int(page),
                "page_size": int(page_size),
                "returned": len(rows),
                "has_more": len(rows) >= int(page_size),
            }
        meta: dict[str, Any] = {}
        normalized_roles = set(normalize_roles_fn(profile.get("roles") or []))
        if "assistant_editor" in normalized_roles and "managing_editor" not in normalized_roles and not manuscript_id:
            raise HTTPException(status_code=422, detail="manuscript_id is required for assistant editor reviewer search")

        if manuscript_id:
            ms_resp = (
                supabase_admin_client.table("manuscripts")
                .select("id,author_id,journal_id,status,assistant_editor_id")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            manuscript = getattr(ms_resp, "data", None) or {}
            if not manuscript:
                raise HTTPException(status_code=404, detail="Manuscript not found")

            if "admin" not in normalized_roles:
                # 纯 AE 仅允许访问自己分管稿件的候选池（ME/Admin 保持现有可见范围）。
                if "assistant_editor" in normalized_roles and "managing_editor" not in normalized_roles:
                    assigned_ae = str(manuscript.get("assistant_editor_id") or "").strip()
                    if assigned_ae != str(profile.get("id") or "").strip():
                        raise HTTPException(status_code=403, detail="Forbidden: manuscript not assigned to current assistant editor")
                elif "managing_editor" not in normalized_roles:
                    raise HTTPException(status_code=403, detail="Insufficient role")

            policy_service = review_policy_service_cls()
            reviewer_ids = [str(r.get("id") or "").strip() for r in rows if str(r.get("id") or "").strip()]
            policy_map = policy_service.evaluate_candidates(manuscript=manuscript, reviewer_ids=reviewer_ids)
            for row in rows:
                rid = str(row.get("id") or "").strip()
                row["invite_policy"] = policy_map.get(rid) or {
                    "can_assign": True,
                    "allow_override": False,
                    "cooldown_active": False,
                    "conflict": False,
                    "overdue_risk": False,
                    "overdue_open_count": 0,
                    "hits": [],
                }
            meta = {
                "cooldown_days": policy_service.cooldown_days(),
                "override_roles": policy_service.cooldown_override_roles(),
            }
        return {"success": True, "data": rows, "policy": meta, "pagination": pagination}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ReviewerLibrary] search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search reviewer library")
