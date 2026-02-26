from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.manuscripts_detail_handlers import (
    download_review_attachment_for_author_impl,
    get_manuscript_author_context_impl,
    get_manuscript_detail_impl,
    get_manuscript_versions_impl,
)
from app.core.auth_utils import get_current_user
from app.core.roles import get_current_profile
from app.models.revision import VersionHistoryResponse

router = APIRouter(tags=["Manuscripts"])


@router.get("/manuscripts/{manuscript_id}/author-context")
async def get_manuscript_author_context(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    return await get_manuscript_author_context_impl(
        manuscript_id=manuscript_id,
        current_user=current_user,
        profile=profile,
    )


@router.get("/manuscripts/{manuscript_id}/review-reports/{report_id}/author-attachment")
async def download_review_attachment_for_author(
    manuscript_id: UUID,
    report_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    return await download_review_attachment_for_author_impl(
        manuscript_id=manuscript_id,
        report_id=report_id,
        current_user=current_user,
        profile=profile,
    )


@router.get("/manuscripts/{manuscript_id}/versions", response_model=VersionHistoryResponse)
async def get_manuscript_versions(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    return await get_manuscript_versions_impl(
        manuscript_id=manuscript_id,
        current_user=current_user,
    )


@router.get("/manuscripts/by-id/{manuscript_id}")
async def get_manuscript_detail(
    manuscript_id: UUID,
    current_user: dict = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
):
    return await get_manuscript_detail_impl(
        manuscript_id=manuscript_id,
        current_user=current_user,
        profile=profile,
    )
