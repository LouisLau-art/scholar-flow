#!/usr/bin/env bash

set -euo pipefail

BEFORE=""
AFTER=""
OUT=""
THRESHOLD="${THRESHOLD_RATIO:-0.10}"

usage() {
  cat <<'USAGE'
Usage: scripts/perf/compare-editor-baseline.sh --before <before.json> --after <after.json> [options]

Options:
  --before <path>         Baseline before JSON (required)
  --after <path>          Baseline after JSON (required)
  --output <path>         Output summary JSON (optional; default stdout only)
  --threshold <ratio>     Regression threshold ratio (default: 0.10)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --before)
      BEFORE="${2:-}"
      shift 2
      ;;
    --after)
      AFTER="${2:-}"
      shift 2
      ;;
    --output)
      OUT="${2:-}"
      shift 2
      ;;
    --threshold)
      THRESHOLD="${2:-0.10}"
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

if [[ -z "$BEFORE" || -z "$AFTER" ]]; then
  echo "--before and --after are required" >&2
  usage
  exit 2
fi

python3 - <<'PY' "$BEFORE" "$AFTER" "$THRESHOLD" "$OUT"
import json
import math
import sys
from datetime import datetime, timezone

before_path, after_path, threshold_raw, out_path = sys.argv[1:]
threshold = float(threshold_raw)

with open(before_path, "r", encoding="utf-8") as f:
    before = json.load(f)
with open(after_path, "r", encoding="utf-8") as f:
    after = json.load(f)

def by_scenario(payload):
    out = {}
    for row in payload.get("records", []):
        scenario = str(row.get("scenario") or "").strip()
        if scenario:
            out[scenario] = row
    return out

before_map = by_scenario(before)
after_map = by_scenario(after)
all_scenarios = sorted(set(before_map.keys()) | set(after_map.keys()))
rows = []

worst_ratio = 0.0
for scenario in all_scenarios:
    b = before_map.get(scenario, {})
    a = after_map.get(scenario, {})
    b_p95 = float(b.get("p95_interactive_ms") or 0)
    a_p95 = float(a.get("p95_interactive_ms") or 0)
    if b_p95 > 0:
        ratio = (a_p95 - b_p95) / b_p95
    else:
        ratio = math.inf if a_p95 > 0 else 0.0
    worst_ratio = max(worst_ratio, ratio if math.isfinite(ratio) else 1.0)
    rows.append(
        {
            "scenario": scenario,
            "before_p95_ms": int(b_p95) if b_p95 else None,
            "after_p95_ms": int(a_p95) if a_p95 else None,
            "regression_ratio": ratio,
            "regressed": bool(math.isfinite(ratio) and ratio > threshold),
        }
    )

status = "passed"
if any(item["regressed"] for item in rows):
    status = "failed"

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "threshold_ratio": threshold,
    "worst_regression_ratio": worst_ratio,
    "status": status,
    "rows": rows,
}

serialized = json.dumps(summary, ensure_ascii=True, indent=2) + "\n"
print(serialized, end="")

if out_path:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(serialized)
PY
