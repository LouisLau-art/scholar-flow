from fastapi import APIRouter, Depends, HTTPException, Query, Request
from uuid import UUID
from typing import Optional
from app.services.doi_service import DOIService
from app.models.doi import DOIRegistration, DOITask, DOITaskList, DOIRegistrationCreate
from app.core.config import CrossrefConfig
from app.lib.api_client import supabase

router = APIRouter(prefix="/doi", tags=["DOI"])


def get_doi_service(request: Request) -> DOIService:
    config = CrossrefConfig.from_env()
    crossref_client = getattr(request.app.state, "crossref_client", None)
    return DOIService(config, crossref_client=crossref_client)


@router.post("/register", response_model=DOIRegistration, status_code=201)
async def register_doi(
    request: DOIRegistrationCreate, service: DOIService = Depends(get_doi_service)
):
    """
    Trigger DOI registration for a published article
    """
    try:
        registration = await service.create_registration(request.article_id)
        return registration
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks", response_model=DOITaskList)
async def list_doi_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """
    List DOI tasks (admin only)
    """
    query = supabase.table("doi_tasks").select("*", count="exact")
    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    res = query.execute()

    return DOITaskList(items=res.data, total=res.count or 0, limit=limit, offset=offset)


@router.get("/tasks/failed", response_model=DOITaskList)
async def list_failed_tasks(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """
    List failed DOI tasks
    """
    query = (
        supabase.table("doi_tasks").select("*", count="exact").eq("status", "failed")
    )
    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    res = query.execute()

    return DOITaskList(items=res.data, total=res.count or 0, limit=limit, offset=offset)


@router.get("/{article_id}", response_model=DOIRegistration)
async def get_doi_status(
    article_id: UUID, service: DOIService = Depends(get_doi_service)
):
    """
    Get DOI registration status by article ID
    """
    registration = await service.get_registration(article_id)
    if not registration:
        raise HTTPException(status_code=404, detail="DOI registration not found")
    return registration


@router.post("/{article_id}/retry", response_model=DOITask)
async def retry_doi_registration(
    article_id: UUID, service: DOIService = Depends(get_doi_service)
):
    """
    Manually retry a failed DOI registration
    """
    # 1. Get registration
    registration = await service.get_registration(article_id)
    if not registration:
        raise HTTPException(status_code=404, detail="DOI registration not found")

    # 2. Check if retry is allowed (failed or pending/stuck?)
    # For simplicity, we allow retry if not 'registered'
    if registration.status == "registered":
        raise HTTPException(status_code=400, detail="DOI already registered")

    # 3. Create new task
    # Using supabase client directly for MVP simplicity or via service
    res = (
        supabase.table("doi_tasks")
        .insert(
            {
                "registration_id": str(registration.id),
                "task_type": "register",
                "status": "pending",
                "priority": 10,  # High priority for manual retry
                "attempts": 0,
                "run_at": "now()",
                "created_at": "now()",
            }
        )
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create retry task")

    return res.data[0]
