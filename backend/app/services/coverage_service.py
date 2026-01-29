import json
from pathlib import Path
import xml.etree.ElementTree as ET


def _parse_backend_coverage(coverage_xml: Path) -> dict:
    # 中文注释: 解析 coverage.xml，提取行覆盖率与分支覆盖率
    tree = ET.parse(coverage_xml)
    root = tree.getroot()

    line_rate = float(root.get("line-rate", "0")) * 100
    branch_rate = float(root.get("branch-rate", "0")) * 100

    return {
        "line_rate": round(line_rate, 2),
        "branch_rate": round(branch_rate, 2),
    }


def _parse_frontend_coverage(coverage_json: Path) -> dict:
    # 中文注释: 解析 vitest 覆盖率输出，统计语句/函数/分支覆盖率
    with coverage_json.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict) and "total" in data:
        total = data["total"]
        return {
            "statement_rate": round(float(total["statements"]["pct"]), 2),
            "function_rate": round(float(total["functions"]["pct"]), 2),
            "branch_rate": round(float(total["branches"]["pct"]), 2),
        }

    total_statements = 0
    covered_statements = 0
    total_functions = 0
    covered_functions = 0
    total_branches = 0
    covered_branches = 0

    for metrics in data.values():
        statements = metrics.get("s", {})
        total_statements += len(statements)
        covered_statements += sum(1 for count in statements.values() if count > 0)

        functions = metrics.get("f", {})
        total_functions += len(functions)
        covered_functions += sum(1 for count in functions.values() if count > 0)

        branches = metrics.get("b", {})
        for branch_hits in branches.values():
            total_branches += len(branch_hits)
            covered_branches += sum(1 for count in branch_hits if count > 0)

    def pct(covered: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round((covered / total) * 100, 2)

    return {
        "statement_rate": pct(covered_statements, total_statements),
        "function_rate": pct(covered_functions, total_functions),
        "branch_rate": pct(covered_branches, total_branches),
    }


def get_coverage_summary() -> dict:
    repo_root = Path(__file__).resolve().parents[3]

    backend_xml = repo_root / "backend" / "coverage.xml"
    frontend_summary = repo_root / "frontend" / "coverage" / "coverage-summary.json"
    frontend_final = repo_root / "frontend" / "coverage" / "coverage-final.json"

    backend = _parse_backend_coverage(backend_xml) if backend_xml.exists() else None

    frontend = None
    if frontend_summary.exists():
        frontend = _parse_frontend_coverage(frontend_summary)
    elif frontend_final.exists():
        frontend = _parse_frontend_coverage(frontend_final)

    return {
        "backend": backend,
        "frontend": frontend,
    }
