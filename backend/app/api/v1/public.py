from fastapi import APIRouter

from app.lib.api_client import supabase_admin

router = APIRouter(prefix="/public", tags=["Public Resources"])


# 中文注释:
# - 由于当前 schema 里没有稳定的“学科分类表”，MVP 先用标题/摘要关键词做轻量归类。
# - 后续若新增 journals.subject/category 字段，可直接切到数据库聚合而不是关键词匹配。
_SUBJECT_COLLECTION_RULES = [
    {
        "id": "medicine",
        "name": "Medicine",
        "icon": "Stethoscope",
        "query": "medicine",
        "keywords": (
            "medicine",
            "medical",
            "clinical",
            "health",
            "patient",
            "disease",
            "therapy",
            "hospital",
            "biomedical",
            "oncology",
        ),
    },
    {
        "id": "technology",
        "name": "Technology",
        "icon": "Cpu",
        "query": "technology",
        "keywords": (
            "technology",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "ai ",
            "algorithm",
            "software",
            "computer",
            "engineering",
            "data science",
            "robot",
            "network",
        ),
    },
    {
        "id": "physics",
        "name": "Physics",
        "icon": "Atom",
        "query": "physics",
        "keywords": (
            "physics",
            "quantum",
            "particle",
            "optics",
            "photon",
            "thermodynamics",
            "astrophysics",
            "materials",
            "nanostructure",
        ),
    },
    {
        "id": "social",
        "name": "Social Sciences",
        "icon": "Landmark",
        "query": "social",
        "keywords": (
            "social",
            "sociology",
            "economics",
            "policy",
            "education",
            "psychology",
            "humanities",
            "law",
            "governance",
            "ethics",
            "management",
        ),
    },
    {
        "id": "general",
        "name": "General Science",
        "icon": "FlaskConical",
        "query": "science",
        "keywords": (),
    },
]


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _load_subject_source_rows() -> list[dict]:
    """
    Subject Collections 数据源（优先已发表文章，其次期刊）。
    """
    try:
        ms_resp = (
            supabase_admin.table("manuscripts")
            .select("title,abstract")
            .eq("status", "published")
            .limit(1200)
            .execute()
        )
        ms_rows = getattr(ms_resp, "data", None) or []
        if ms_rows:
            return list(ms_rows)
    except Exception:
        pass

    try:
        jr_resp = (
            supabase_admin.table("journals")
            .select("title,description")
            .limit(400)
            .execute()
        )
        jr_rows = getattr(jr_resp, "data", None) or []
        return list(jr_rows)
    except Exception:
        return []


def _aggregate_subject_counts(rows: list[dict]) -> dict[str, int]:
    counts = {rule["id"]: 0 for rule in _SUBJECT_COLLECTION_RULES}
    for row in rows:
        text = _normalize_text(
            f"{row.get('title') or ''} {row.get('abstract') or row.get('description') or ''}"
        )
        if not text:
            continue

        matched = False
        for rule in _SUBJECT_COLLECTION_RULES:
            keywords = tuple(rule.get("keywords") or ())
            if not keywords:
                continue
            if any(keyword in text for keyword in keywords):
                counts[str(rule["id"])] += 1
                matched = True

        if not matched:
            counts["general"] += 1

    return counts


@router.get("/topics")
async def get_all_topics():
    """
    获取 Subject Collections（用于发现页）
    """
    rows = _load_subject_source_rows()
    counts = _aggregate_subject_counts(rows)

    collections = []
    for rule in _SUBJECT_COLLECTION_RULES:
        count = int(counts.get(str(rule["id"]), 0))
        if count <= 0:
            continue
        collections.append(
            {
                "id": rule["id"],
                "name": rule["name"],
                "icon": rule["icon"],
                "count": count,
                "query": rule["query"],
                "metric_label": "Articles",
            }
        )

    if not collections:
        collections = [
            {"id": "medicine", "name": "Medicine", "icon": "Stethoscope", "count": 0, "query": "medicine", "metric_label": "Articles"},
            {"id": "technology", "name": "Technology", "icon": "Cpu", "count": 0, "query": "technology", "metric_label": "Articles"},
            {"id": "physics", "name": "Physics", "icon": "Atom", "count": 0, "query": "physics", "metric_label": "Articles"},
            {"id": "social", "name": "Social Sciences", "icon": "Landmark", "count": 0, "query": "social", "metric_label": "Articles"},
        ]
    else:
        collections.sort(key=lambda item: (-int(item["count"]), str(item["name"])))

    return {
        "success": True,
        "data": collections,
    }

@router.get("/announcements")
async def get_announcements():
    """
    获取平台系统公告
    """
    return {
        "success": True,
        "data": [
            {"id": 1, "title": "Call for Papers: AI in Healthcare", "tag": "Event", "date": "2026-02-01"},
            {"id": 2, "title": "ScholarFlow 2.0 Maintenance Schedule", "tag": "System", "date": "2026-01-30"}
        ]
    }
