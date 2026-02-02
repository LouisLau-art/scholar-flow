import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_line_coverage_reported():
    """覆盖率文件不存在时跳过；存在时验证行覆盖率字段"""
    repo_root = load_repo_path()
    coverage_xml = repo_root / "backend" / "coverage.xml"

    if not coverage_xml.exists():
        pytest.skip("Coverage XML not generated")

    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    line_rate = float(root.get("line-rate", "0"))
    assert 0.0 <= line_rate <= 1.0
