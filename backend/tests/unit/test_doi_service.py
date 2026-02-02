import pytest
from uuid import UUID

from app.core.config import CrossrefConfig
from app.services.doi_service import DOIService


def test_generate_doi_defaults_without_config():
    svc = DOIService()
    assert svc.generate_doi(2026, 1) == "10.12345/sf.2026.00001"


def test_generate_doi_uses_config_prefix():
    cfg = CrossrefConfig(
        depositor_email="x@example.com",
        depositor_password="pw",
        doi_prefix="10.99999",
        api_url="https://example.com",
        journal_title="J",
        journal_issn=None,
    )
    svc = DOIService(config=cfg)
    assert svc.generate_doi(2026, 2) == "10.99999/sf.2026.00002"


@pytest.mark.asyncio
async def test_get_registration_returns_none_for_unknown_id():
    svc = DOIService()
    assert await svc.get_registration(UUID("11111111-1111-1111-1111-111111111111")) is None


@pytest.mark.asyncio
async def test_get_registration_returns_record_for_magic_id():
    svc = DOIService()
    reg = await svc.get_registration(UUID("00000000-0000-0000-0000-000000000000"))
    assert reg is not None
    assert str(reg.article_id) == "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_register_doi_placeholder_executes():
    svc = DOIService()
    # Placeholder implementation should be awaitable and not raise.
    await svc.register_doi(UUID("00000000-0000-0000-0000-000000000000"))

