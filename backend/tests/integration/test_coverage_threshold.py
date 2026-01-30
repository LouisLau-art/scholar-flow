import configparser
from pathlib import Path


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


def test_backend_coverage_threshold_configured():
    """验证后端覆盖率阈值配置为 80%"""
    repo_root = load_repo_path()
    coveragerc = repo_root / "backend" / ".coveragerc"
    pytest_ini = repo_root / "backend" / "pytest.ini"

    config = configparser.ConfigParser()
    config.read(coveragerc)
    assert config.has_option("report", "fail_under")
    assert int(config.get("report", "fail_under")) >= 80

    pytest_text = pytest_ini.read_text(encoding="utf-8")
    assert "--cov-fail-under=80" in pytest_text
