#!/usr/bin/env bash

set -euo pipefail

OUT=""
ENVIRONMENT="${ENVIRONMENT:-staging}"
SAMPLE_SET_ID="${SAMPLE_SET_ID:-editor-perf-v1}"
CAPTURED_BY="${CAPTURED_BY:-${USER:-unknown}}"
SCENARIO="${SCENARIO:-editor_detail}"
P50="${P50_INTERACTIVE_MS:-0}"
P95="${P95_INTERACTIVE_MS:-0}"
REQ_COUNT="${FIRST_SCREEN_REQUEST_COUNT:-0}"
NOTES="${NOTES:-}"

usage() {
  cat <<'USAGE'
Usage: scripts/perf/capture-editor-baseline.sh --output <path> [options]

Options:
  --output <path>         Output JSON path (required)
  --environment <value>   staging | local-ci (default: staging)
  --sample-set <value>    Sample set id (default: editor-perf-v1)
  --captured-by <value>   Operator id/name
  --scenario <value>      editor_detail | editor_process | editor_workspace | reviewer_search_repeat
  --p50 <ms>              p50 interactive time (required via arg/env)
  --p95 <ms>              p95 interactive time (required via arg/env)
  --requests <count>      First screen request count (required via arg/env)
  --notes <text>          Optional notes
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUT="${2:-}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="${2:-}"
      shift 2
      ;;
    --sample-set)
      SAMPLE_SET_ID="${2:-}"
      shift 2
      ;;
    --captured-by)
      CAPTURED_BY="${2:-}"
      shift 2
      ;;
    --scenario)
      SCENARIO="${2:-}"
      shift 2
      ;;
    --p50)
      P50="${2:-0}"
      shift 2
      ;;
    --p95)
      P95="${2:-0}"
      shift 2
      ;;
    --requests)
      REQ_COUNT="${2:-0}"
      shift 2
      ;;
    --notes)
      NOTES="${2:-}"
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

if [[ -z "$OUT" ]]; then
  echo "--output is required" >&2
  usage
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

python3 - <<'PY' "$OUT" "$ENVIRONMENT" "$SAMPLE_SET_ID" "$CAPTURED_BY" "$SCENARIO" "$P50" "$P95" "$REQ_COUNT" "$NOTES"
import json
import sys
from datetime import datetime, timezone

out, environment, sample_set_id, captured_by, scenario, p50, p95, req_count, notes = sys.argv[1:]

payload = {
    "environment": environment,
    "sample_set_id": sample_set_id,
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "captured_by": captured_by,
    "records": [
        {
            "scenario": scenario,
            "p50_interactive_ms": int(p50),
            "p95_interactive_ms": int(p95),
            "first_screen_request_count": int(req_count),
            "notes": notes or None,
        }
    ],
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=True, indent=2)
    f.write("\n")
PY

echo "[capture-editor-baseline] wrote $OUT"
