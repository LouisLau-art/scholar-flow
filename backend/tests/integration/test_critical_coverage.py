import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_critical_paths_full_coverage():
    """
    关键路径 100% 覆盖率检查（需要显式启用）。
    通过环境变量 COVERAGE_STRICT=1 控制严格模式。
    """
    if not os.environ.get("COVERAGE_STRICT"):
        pytest.skip("Set COVERAGE_STRICT=1 to enforce 100% critical coverage")

    repo_root = load_repo_path()
    coverage_xml = repo_root / "backend" / "coverage.xml"
    if not coverage_xml.exists():
        pytest.skip("Coverage XML not generated")

    critical_files = {
        "app/core/auth_utils.py",
    }

    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    coverage_map = {}
    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if filename:
            coverage_map[filename] = float(cls.get("line-rate", "0"))

    for critical in critical_files:
        rate = coverage_map.get(critical)
        assert rate is not None, f"Missing coverage data for {critical}"
        assert rate >= 1.0, f"{critical} coverage {rate * 100:.1f}% < 100%"
