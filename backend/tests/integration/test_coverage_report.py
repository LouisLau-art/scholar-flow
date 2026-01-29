import configparser
import os
from pathlib import Path

import pytest


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


def load_coveragerc() -> configparser.ConfigParser:
    repo_root = load_repo_path()
    config = configparser.ConfigParser()
    config.read(repo_root / "backend" / ".coveragerc")
    return config


def test_backend_coverage_config_present():
    """验证后端覆盖率配置文件存在且可读取"""
    repo_root = load_repo_path()
    coveragerc = repo_root / "backend" / ".coveragerc"
    assert coveragerc.exists()
    config = load_coveragerc()
    assert "run" in config
    assert "report" in config


@pytest.mark.integration
def test_coverage_report_artifacts_exist_when_generated():
    """覆盖率文件不存在时跳过；存在时验证关键文件路径"""
    repo_root = load_repo_path()
    coverage_xml = repo_root / "backend" / "coverage.xml"
    htmlcov = repo_root / "backend" / "htmlcov" / "index.html"

    if not coverage_xml.exists() and not htmlcov.exists():
        pytest.skip("Coverage artifacts not generated")

    if coverage_xml.exists():
        assert coverage_xml.stat().st_size > 0
    if htmlcov.exists():
        assert htmlcov.stat().st_size > 0
