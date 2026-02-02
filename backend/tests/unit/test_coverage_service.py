import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.services import coverage_service


def write_sample_backend_coverage(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "<?xml version=\"1.0\" ?>\n"
        "<coverage line-rate=\"0.85\" branch-rate=\"0.9\" version=\"7.5\" timestamp=\"0\">\n"
        "  <packages />\n"
        "</coverage>\n",
        encoding="utf-8",
    )


def write_sample_frontend_coverage(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "file.tsx": {
                    "s": {"1": 1, "2": 0},
                    "f": {"1": 1},
                    "b": {"1": [1, 0]},
                }
            }
        ),
        encoding="utf-8",
    )


def test_parse_backend_coverage(tmp_path: Path):
    coverage_xml = tmp_path / "coverage.xml"
    write_sample_backend_coverage(coverage_xml)

    parsed = coverage_service._parse_backend_coverage(coverage_xml)

    assert parsed["line_rate"] == 85.0
    assert parsed["branch_rate"] == 90.0


def test_parse_frontend_coverage(tmp_path: Path):
    coverage_json = tmp_path / "coverage-final.json"
    write_sample_frontend_coverage(coverage_json)

    parsed = coverage_service._parse_frontend_coverage(coverage_json)

    assert parsed["statement_rate"] == 50.0
    assert parsed["function_rate"] == 100.0
    assert parsed["branch_rate"] == 50.0


@pytest.mark.asyncio
async def test_coverage_endpoint_returns_summary(client: AsyncClient, auth_token: str):
    repo_root = Path(__file__).resolve().parents[3]
    backend_xml = repo_root / "backend" / "coverage.xml"
    frontend_json = repo_root / "frontend" / "coverage" / "coverage-final.json"

    backend_original = backend_xml.read_text(encoding="utf-8") if backend_xml.exists() else None
    frontend_original = frontend_json.read_text(encoding="utf-8") if frontend_json.exists() else None

    write_sample_backend_coverage(backend_xml)
    write_sample_frontend_coverage(frontend_json)

    try:
        response = await client.get(
            "/api/v1/coverage",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["coverage"]["backend"]["line_rate"] == 85.0
        assert payload["coverage"]["thresholds"]["backend_ok"] is True
        assert payload["coverage"]["thresholds"]["frontend_ok"] is False
    finally:
        if backend_original is None:
            backend_xml.unlink(missing_ok=True)
        else:
            backend_xml.write_text(backend_original, encoding="utf-8")

        if frontend_original is None:
            frontend_json.unlink(missing_ok=True)
        else:
            frontend_json.write_text(frontend_original, encoding="utf-8")
