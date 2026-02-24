#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FEATURE_KEY="${FEATURE_KEY:-001-editor-performance-refactor}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$ROOT_DIR/specs/001-editor-performance-refactor/artifacts}"
BEFORE_PATH="${BEFORE_PATH:-$ARTIFACT_DIR/baseline-before.json}"
AFTER_PATH="${AFTER_PATH:-$ARTIFACT_DIR/baseline-after.json}"
COMPARE_PATH="${COMPARE_PATH:-$ARTIFACT_DIR/baseline-compare.json}"
REPORT_PATH="${REPORT_PATH:-$ARTIFACT_DIR/regression-report.md}"
THRESHOLD_RATIO="${THRESHOLD_RATIO:-0.10}"
RUN_RELEASE_VALIDATION="${RUN_RELEASE_VALIDATION:-0}"

if [[ ! -f "$BEFORE_PATH" || ! -f "$AFTER_PATH" ]]; then
  echo "[validate-editor-performance] missing baseline file(s)" >&2
  echo "- before: $BEFORE_PATH" >&2
  echo "- after : $AFTER_PATH" >&2
  exit 2
fi

mkdir -p "$ARTIFACT_DIR"

"$ROOT_DIR/scripts/perf/compare-editor-baseline.sh" \
  --before "$BEFORE_PATH" \
  --after "$AFTER_PATH" \
  --threshold "$THRESHOLD_RATIO" \
  --output "$COMPARE_PATH"

"$ROOT_DIR/scripts/perf/write-regression-report.sh" \
  --summary "$COMPARE_PATH" \
  --output "$REPORT_PATH"

if [[ "$RUN_RELEASE_VALIDATION" == "1" ]]; then
  "$ROOT_DIR/scripts/validate-production-rollout.sh" \
    --feature-key "$FEATURE_KEY"
fi

python3 - <<'PY' "$COMPARE_PATH"
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
status = str(data.get("status") or "failed").lower()
if status != "passed":
    print("[validate-editor-performance] NO-GO: regression gate failed")
    raise SystemExit(1)
print("[validate-editor-performance] GO: regression gate passed")
PY
