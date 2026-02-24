#!/usr/bin/env bash

set -euo pipefail

SUMMARY=""
OUT=""

usage() {
  cat <<'USAGE'
Usage: scripts/perf/write-regression-report.sh --summary <summary.json> --output <report.md>
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --summary)
      SUMMARY="${2:-}"
      shift 2
      ;;
    --output)
      OUT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$SUMMARY" || -z "$OUT" ]]; then
  echo "--summary and --output are required" >&2
  usage
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

python3 - <<'PY' "$SUMMARY" "$OUT"
import json
import math
import sys
from pathlib import Path

summary_path, out_path = sys.argv[1:]
with open(summary_path, "r", encoding="utf-8") as f:
    data = json.load(f)

status = str(data.get("status") or "failed").lower()
status_label = "GO" if status == "passed" else "NO-GO"

lines = [
    "# Regression Gate Report",
    "",
    f"- Generated At: `{data.get('generated_at', '-')}`",
    f"- Threshold Ratio: `{data.get('threshold_ratio', '-')}`",
    f"- Worst Regression Ratio: `{data.get('worst_regression_ratio', '-')}`",
    f"- Decision: **{status_label}**",
    "",
    "| Scenario | Before p95 (ms) | After p95 (ms) | Regression Ratio | Regressed |",
    "|---|---:|---:|---:|---|",
]

for row in data.get("rows", []):
    ratio = row.get("regression_ratio")
    if isinstance(ratio, (int, float)) and math.isfinite(ratio):
      ratio_text = f"{ratio:.4f}"
    else:
      ratio_text = "inf"
    lines.append(
        "| {scenario} | {before} | {after} | {ratio} | {regressed} |".format(
            scenario=row.get("scenario", "-"),
            before=row.get("before_p95_ms", "-"),
            after=row.get("after_p95_ms", "-"),
            ratio=ratio_text,
            regressed="yes" if row.get("regressed") else "no",
        )
    )

Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

echo "[write-regression-report] wrote $OUT"
