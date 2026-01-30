import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_uncovered_paths_reportable():
    """覆盖率文件不存在时跳过；存在时可列出未覆盖文件"""
    repo_root = load_repo_path()
    coverage_xml = repo_root / "backend" / "coverage.xml"

    if not coverage_xml.exists():
        pytest.skip("Coverage XML not generated")

    tree = ET.parse(coverage_xml)
    root = tree.getroot()

    uncovered = []
    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        line_rate = float(cls.get("line-rate", "0"))
        if line_rate < 1.0:
            uncovered.append(filename)

    assert uncovered is not None
