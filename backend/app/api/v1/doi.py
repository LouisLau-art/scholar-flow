from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import CrossrefConfig
from app.models.doi import DOIRegistration, DOITask, DOITaskList, DOIRegistrationCreate
from app.services.doi_service import DOIService

router = APIRouter(prefix="/doi", tags=["DOI"])


def get_doi_service() -> DOIService:
    config = CrossrefConfig.from_env()
    return DOIService(config)


@router.post("/register", response_model=DOIRegistration, status_code=201)
async def register_doi(
    request: DOIRegistrationCreate,
    service: DOIService = Depends(get_doi_service),
):
    """
    Trigger DOI registration for a published manuscript.
    """
    try:
        return await service.create_registration(request.article_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DOI registration: {e}") from e


@router.get("/{article_id}", response_model=DOIRegistration)
async def get_doi_status(
    article_id: UUID,
    service: DOIService = Depends(get_doi_service),
):
    """
    Get DOI registration status by article/manuscript ID.
    """
    registration = await service.get_registration(article_id)
    if not registration:
        raise HTTPException(status_code=404, detail="DOI registration not found")
    return registration


@router.post("/{article_id}/retry", response_model=DOITask)
async def retry_doi_registration(
    article_id: UUID,
    service: DOIService = Depends(get_doi_service),
):
    """
    Manually retry a failed/pending DOI registration.
    """
    return await service.retry_registration(article_id)


@router.get("/tasks", response_model=DOITaskList)
async def list_doi_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DOIService = Depends(get_doi_service),
):
    """
    List DOI tasks.
    """
    return await service.list_tasks(status=status, limit=limit, offset=offset)


@router.get("/tasks/failed", response_model=DOITaskList)
async def list_failed_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DOIService = Depends(get_doi_service),
):
    """
    List failed DOI tasks.
    """
    return await service.list_tasks(failed_only=True, limit=limit, offset=offset)
