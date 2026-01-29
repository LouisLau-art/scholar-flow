import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def load_repo_path() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_function_coverage_placeholder():
    """
    coverage.xml 不包含函数覆盖率字段时跳过；
    仅用于确保覆盖率元数据可扩展。
    """
    repo_root = load_repo_path()
    coverage_xml = repo_root / "backend" / "coverage.xml"

    if not coverage_xml.exists():
        pytest.skip("Coverage XML not generated")

    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    function_rate = root.get("function-rate")
    if function_rate is None:
        pytest.skip("Coverage XML does not provide function-rate")

    rate = float(function_rate)
    assert 0.0 <= rate <= 1.0
