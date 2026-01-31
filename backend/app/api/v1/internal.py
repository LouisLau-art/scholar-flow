import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import psycopg2
from psycopg2 import sql
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import allow_test_endpoints
from app.lib.api_client import supabase_admin

from app.core.scheduler import ChaseScheduler
from app.core.security import require_admin_key, require_admin_bearer_key

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/cron/chase-reviews")
async def chase_reviews(_admin: None = Depends(require_admin_key)):
    """
    触发自动催办逻辑（内部接口）
    """
    scheduler = ChaseScheduler()
    result = scheduler.run()
    return {"success": True, **result}


def _get_test_db_url() -> str:
    """
    获取测试数据库连接串。

    中文注释:
    - 优先读取 TEST_DB_URL，避免误连生产库。
    - 若未设置，允许回退到 DATABASE_URL / SUPABASE_DB_URL（仅用于本地开发）。
    """

    for key in ("TEST_DB_URL", "DATABASE_URL", "SUPABASE_DB_URL"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return raw
    return ""


def _truncate_public_tables(db_url: str) -> List[str]:
    """
    TRUNCATE public schema 下的业务表（RESTART IDENTITY + CASCADE）。

    返回实际被清理的表名列表。
    """

    conn = psycopg2.connect(db_url)
    try:
        conn.set_session(autocommit=True)
        with conn.cursor() as cur:
            cur.execute(
                "select tablename from pg_tables where schemaname = 'public' order by tablename"
            )
            tables = [r[0] for r in cur.fetchall() if r and r[0]]

            # 中文注释: 排除少量“扩展/系统”表（如存在），避免误删扩展自带数据
            deny = {"spatial_ref_sys"}
            tables = [t for t in tables if t not in deny]

            if not tables:
                return []

            identifiers = [sql.Identifier("public", t) for t in tables]
            query = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(identifiers)
            )
            cur.execute(query)
            return tables
    finally:
        conn.close()


@router.post("/reset-db")
async def reset_db(_admin: None = Depends(require_admin_bearer_key)) -> Dict[str, Any]:
    """
    Reset Database（测试专用）

    - 仅在 ENABLE_TEST_ENDPOINTS / GO_ENV=test|dev 时允许
    - 通过 TRUNCATE 清空 public schema 业务数据
    """

    if not allow_test_endpoints():
        raise HTTPException(status_code=403, detail="Test endpoints are disabled")

    db_url = _get_test_db_url()
    if not db_url:
        raise HTTPException(status_code=500, detail="TEST_DB_URL not configured")

    try:
        tables = _truncate_public_tables(db_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database reset failed: {e}")

    return {
        "message": "Database reset complete.",
        "tables_truncated": tables,
        "at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/seed-db")
async def seed_db(_admin: None = Depends(require_admin_bearer_key)) -> Dict[str, Any]:
    """
    Seed Database（测试专用）

    中文注释:
    - 该端点通过 Supabase Admin API 创建测试用户（固定 UUID）
    - 并写入 user_profiles / journals / manuscripts / review_assignments 等基础数据
    """

    if not allow_test_endpoints():
        raise HTTPException(status_code=403, detail="Test endpoints are disabled")

    # 1) 创建测试用户（Supabase Auth）
    users = [
        ("author", "author@example.com", "password123", "11111111-1111-4111-a111-111111111111"),
        ("reviewer1", "reviewer1@example.com", "password123", "22222222-2222-4222-a222-222222222222"),
        ("reviewer2", "reviewer2@example.com", "password123", "33333333-3333-4333-a333-333333333333"),
        ("editor", "editor@example.com", "password123", "44444444-4444-4444-a444-444444444444"),
        ("admin", "admin@example.com", "password123", "55555555-5555-4555-a555-555555555555"),
    ]

    created_users = 0
    for _, email, password, uid in users:
        try:
            supabase_admin.auth.admin.get_user_by_id(uid)
        except Exception:
            # 不存在则创建
            supabase_admin.auth.admin.create_user(
                {
                    "id": uid,
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                }
            )
            created_users += 1

    # 2) 写入 user_profiles（应用层 RBAC）
    role_map = {
        "author@example.com": ["author"],
        "reviewer1@example.com": ["reviewer"],
        "reviewer2@example.com": ["reviewer"],
        "editor@example.com": ["editor"],
        "admin@example.com": ["admin", "editor", "reviewer", "author"],
    }
    for _, email, _pwd, uid in users:
        roles = role_map.get(email, ["author"])
        supabase_admin.table("user_profiles").upsert(
            {"id": uid, "email": email, "roles": roles}
        ).execute()

    # 3) Seed 一个 Journal
    journal_res = (
        supabase_admin.table("journals")
        .upsert(
            {
                "slug": "jat",
                "title": "Journal of Advanced Testing",
                "description": "A journal dedicated to testing the Scholar Flow platform.",
                "issn": "1234-5678",
            },
            on_conflict="slug",
        )
        .select("*")
        .single()
        .execute()
    )
    journal = getattr(journal_res, "data", None) or {}
    journal_id = journal.get("id")
    if not journal_id:
        raise HTTPException(status_code=500, detail="Failed to seed journals")

    # 4) Seed Manuscripts（覆盖多个状态）
    manuscripts_payload: List[Dict[str, Any]] = [
        {
            "title": "The Impact of Automated Testing",
            "abstract": "Seeded manuscript for E2E Author/Editor flows.",
            "author_id": users[0][3],
            "editor_id": users[3][3],
            "status": "submitted",
            "journal_id": journal_id,
        },
        {
            "title": "Algorithms for Peer Review",
            "abstract": "Seeded manuscript under review.",
            "author_id": users[0][3],
            "editor_id": users[3][3],
            "status": "under_review",
            "journal_id": journal_id,
        },
        {
            "title": "Ready for Decision",
            "abstract": "Seeded manuscript ready for decision.",
            "author_id": users[0][3],
            "editor_id": users[3][3],
            "status": "pending_decision",
            "journal_id": journal_id,
        },
        {
            "title": "Finalized Research Paper",
            "abstract": "Seeded accepted manuscript.",
            "author_id": users[0][3],
            "editor_id": users[3][3],
            "status": "accepted",
            "journal_id": journal_id,
        },
        {
            "title": "Flawed Methodology",
            "abstract": "Seeded rejected manuscript.",
            "author_id": users[0][3],
            "editor_id": users[3][3],
            "status": "rejected",
            "journal_id": journal_id,
        },
    ]

    ms_res = (
        supabase_admin.table("manuscripts")
        .insert(manuscripts_payload)
        .select("id,title,status")
        .execute()
    )
    manuscripts = ms_res.data or []
    if len(manuscripts) < 2:
        raise HTTPException(status_code=500, detail="Failed to seed manuscripts")

    # 5) Seed Review Assignments（给 under_review 的稿件分配 reviewer1）
    under_review_id = None
    for ms in manuscripts:
        if ms.get("status") == "under_review":
            under_review_id = ms.get("id")
            break

    if under_review_id:
        try:
            supabase_admin.table("review_assignments").insert(
                {
                    "manuscript_id": under_review_id,
                    "reviewer_id": users[1][3],
                    "status": "pending",
                }
            ).execute()
        except Exception as e:
            # 中文注释: 若 review_assignments 缺列（如 scores/comments），不阻塞 seed
            print(f"[seed-db] review_assignments 插入失败（降级继续）: {e}")

    return {
        "message": "Database seeded successfully.",
        "summary": {
            "users_created": created_users,
            "manuscripts_created": len(manuscripts),
        },
    }
