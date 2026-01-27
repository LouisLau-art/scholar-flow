from fastapi import APIRouter
from app.lib.api_client import supabase

router = APIRouter(prefix="/public", tags=["Public Resources"])

@router.get("/topics")
async def get_all_topics():
    """
    获取所有学科分类列表 (用于发现页)
    """
    return {
        "success": True,
        "data": [
            {"id": "med", "name": "Medicine", "icon": "Stethoscope", "count": 42},
            {"id": "tech", "name": "Technology", "icon": "Cpu", "count": 38},
            {"id": "phys", "name": "Physics", "icon": "Atom", "count": 25},
            {"id": "soc", "name": "Social Sciences", "icon": "Landmark", "count": 22}
        ]
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
