#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
CAPTURE_SCRIPT="$ROOT_DIR/scripts/perf/capture-editor-baseline.sh"

OUT_DIR="${OUT_DIR:-$ROOT_DIR/specs/001-editor-performance-refactor/artifacts}"
PREFIX="${PREFIX:-baseline-api}"
BASE_URL="${BASE_URL:-}"
TOKEN="${TOKEN:-}"
MANUSCRIPT_ID="${MANUSCRIPT_ID:-}"
SAMPLES="${SAMPLES:-10}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
SAMPLE_SET_ID="${SAMPLE_SET_ID:-editor-perf-v1}"
CAPTURED_BY="${CAPTURED_BY:-${USER:-unknown}}"
REQUEST_COUNT="${REQUEST_COUNT:-1}"

usage() {
  cat <<'USAGE'
Usage: scripts/perf/capture-editor-api-baselines.sh [options]

Options:
  --out-dir <path>        Output directory (default: specs/.../artifacts)
  --prefix <name>         Output file prefix (default: baseline-api)
  --base-url <url>        Backend base URL (required)
  --token <bearer>        Bearer token (required)
  --manuscript-id <uuid>  Manuscript UUID for detail scenario (required)
  --samples <count>       Probe sample count (default: 10)
  --environment <value>   staging | local-ci (default: staging)
  --sample-set <value>    Sample set id (default: editor-perf-v1)
  --captured-by <value>   Operator id/name
  --requests <count>      First screen request count placeholder (default: 1)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    --prefix)
      PREFIX="${2:-}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --token)
      TOKEN="${2:-}"
      shift 2
      ;;
    --manuscript-id)
      MANUSCRIPT_ID="${2:-}"
      shift 2
      ;;
    --samples)
      SAMPLES="${2:-10}"
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
    --requests)
      REQUEST_COUNT="${2:-1}"
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

if [[ -z "$BASE_URL" || -z "$TOKEN" || -z "$MANUSCRIPT_ID" ]]; then
  echo "--base-url, --token, --manuscript-id are required" >&2
  usage
  exit 2
fi

mkdir -p "$OUT_DIR"
BASE_URL="${BASE_URL%/}"

echo "[capture-editor-api-baselines] sampling editor_detail ..."
"$CAPTURE_SCRIPT" \
  --output "$OUT_DIR/${PREFIX}-editor_detail.json" \
  --environment "$ENVIRONMENT" \
  --sample-set "$SAMPLE_SET_ID" \
  --captured-by "$CAPTURED_BY" \
  --scenario "editor_detail" \
  --requests "$REQUEST_COUNT" \
  --auto-url "$BASE_URL/api/v1/editor/manuscripts/${MANUSCRIPT_ID}?skip_cards=true" \
  --token "$TOKEN" \
  --samples "$SAMPLES"

echo "[capture-editor-api-baselines] sampling editor_process ..."
"$CAPTURE_SCRIPT" \
  --output "$OUT_DIR/${PREFIX}-editor_process.json" \
  --environment "$ENVIRONMENT" \
  --sample-set "$SAMPLE_SET_ID" \
  --captured-by "$CAPTURED_BY" \
  --scenario "editor_process" \
  --requests "$REQUEST_COUNT" \
  --auto-url "$BASE_URL/api/v1/editor/manuscripts/process" \
  --token "$TOKEN" \
  --samples "$SAMPLES"

echo "[capture-editor-api-baselines] sampling editor_workspace ..."
"$CAPTURE_SCRIPT" \
  --output "$OUT_DIR/${PREFIX}-editor_workspace.json" \
  --environment "$ENVIRONMENT" \
  --sample-set "$SAMPLE_SET_ID" \
  --captured-by "$CAPTURED_BY" \
  --scenario "editor_workspace" \
  --requests "$REQUEST_COUNT" \
  --auto-url "$BASE_URL/api/v1/editor/workspace?page=1&page_size=20" \
  --token "$TOKEN" \
  --samples "$SAMPLES"

echo "[capture-editor-api-baselines] sampling editor_pipeline ..."
"$CAPTURE_SCRIPT" \
  --output "$OUT_DIR/${PREFIX}-editor_pipeline.json" \
  --environment "$ENVIRONMENT" \
  --sample-set "$SAMPLE_SET_ID" \
  --captured-by "$CAPTURED_BY" \
  --scenario "editor_pipeline" \
  --requests "$REQUEST_COUNT" \
  --auto-url "$BASE_URL/api/v1/editor/pipeline" \
  --token "$TOKEN" \
  --samples "$SAMPLES"

echo "[capture-editor-api-baselines] done: $OUT_DIR/${PREFIX}-editor_*.json"
