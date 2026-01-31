from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.lib.api_client import supabase, supabase_admin
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.core.auth import get_current_user_token, get_current_user_roles

router = APIRouter()


@router.post("/system/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    feedback: FeedbackCreate,
    # Optional auth: if user is logged in, we get their ID.
    # But this endpoint is public (for login page feedback), so auth is not strict dependency.
    # We'll try to extract user_id if token is present, but frontend sends it explicitly in payload if known.
):
    """
    Submit feedback from the UAT widget.
    """
    data = feedback.model_dump()

    # Insert into DB
    try:
        response = supabase.table("uat_feedback").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save feedback")

        return response.data[0]
    except Exception as e:
        print(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/feedback", response_model=dict)
async def list_feedback(
    page: int = 1,
    limit: int = 20,
    severity: Optional[str] = None,
    # Auth required for admin view
    token: str = Depends(get_current_user_token),
    roles: List[str] = Depends(get_current_user_roles),
):
    """
    List feedback for admin review.
    """
    # Check permissions
    if "admin" not in roles and "editor" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Pagination
    offset = (page - 1) * limit

    query = supabase.table("uat_feedback").select("*", count="exact")

    if severity:
        query = query.eq("severity", severity)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    result = query.execute()

    total = result.count if result.count is not None else 0
    pages = (total + limit - 1) // limit

    return {"items": result.data, "total": total, "page": page, "pages": pages}
