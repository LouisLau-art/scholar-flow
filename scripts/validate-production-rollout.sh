#!/usr/bin/env bash

set -euo pipefail

EXIT_OK=0
EXIT_NO_GO=1
EXIT_CONFIG=2
EXIT_RUNTIME=3

BASE_URL="${BASE_URL:-${RELEASE_VALIDATION_BASE_URL:-}}"
ADMIN_KEY="${ADMIN_API_KEY:-}"
FEATURE_KEY="${FEATURE_KEY:-042-production-pipeline}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
MANUSCRIPT_ID="${MANUSCRIPT_ID:-}"
READINESS_ONLY=0
DRY_RUN=0
STRICT_BLOCKING=1
REQUIRE_ZERO_SKIP=1
FORCE_NO_GO=0

HTTP_STATUS=""
HTTP_BODY=""

usage() {
  cat <<'EOF'
Usage: scripts/validate-production-rollout.sh [options]

Options:
  --base-url <url>           Backend base URL (e.g. https://xxx.hf.space)
  --api-base <url>           Alias of --base-url (backward compatible)
  --admin-key <key>          ADMIN_API_KEY value
  --feature-key <key>        Feature key (default: 042-production-pipeline)
  --environment <name>       Validation environment (default: staging)
  --manuscript-id <uuid>     Regression target manuscript id (recommended)
  --readiness-only           Only execute readiness checks
  --strict-blocking <0|1>    Readiness gate strict mode (default: 1)
  --require-zero-skip <0|1>  Regression zero-skip gate (default: 1)
  --force-no-go              Force finalize decision to no-go
  --dry-run                  Print execution plan only
  -h, --help                 Show help

Exit Codes:
  0: go / passed
  1: no-go / blocked / failed
  2: config or argument error
  3: runtime error (network/api/jq parsing)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url|--api-base)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --admin-key)
      ADMIN_KEY="${2:-}"
      shift 2
      ;;
    --feature-key)
      FEATURE_KEY="${2:-}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="${2:-}"
      shift 2
      ;;
    --manuscript-id)
      MANUSCRIPT_ID="${2:-}"
      shift 2
      ;;
    --readiness-only)
      READINESS_ONLY=1
      shift
      ;;
    --strict-blocking)
      STRICT_BLOCKING="${2:-1}"
      shift 2
      ;;
    --require-zero-skip)
      REQUIRE_ZERO_SKIP="${2:-1}"
      shift 2
      ;;
    --force-no-go)
      FORCE_NO_GO=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit "${EXIT_OK}"
      ;;
    *)
      echo "[validate-rollout] unknown option: $1" >&2
      usage
      exit "${EXIT_CONFIG}"
      ;;
  esac
done

require_bin() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "[validate-rollout] missing dependency: $name" >&2
    exit "${EXIT_CONFIG}"
  fi
}

normalize_bool() {
  local raw="${1:-0}"
  case "${raw}" in
    1|true|TRUE|yes|YES|on|ON|y|Y) echo "true" ;;
    *) echo "false" ;;
  esac
}

request_json() {
  local method="$1"
  local path="$2"
  local payload="${3:-}"
  local tmp_file
  tmp_file="$(mktemp)"

  if [[ "$method" == "GET" ]]; then
    HTTP_STATUS="$(
      curl -sS -o "$tmp_file" -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1${path}" \
        -H "X-Admin-Key: ${ADMIN_KEY}" \
        -H "Content-Type: application/json"
    )"
  else
    HTTP_STATUS="$(
      curl -sS -o "$tmp_file" -w "%{http_code}" \
        -X "$method" "${BASE_URL}/api/v1${path}" \
        -H "X-Admin-Key: ${ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "${payload}"
    )"
  fi
  HTTP_BODY="$(cat "$tmp_file")"
  rm -f "$tmp_file"
}

if [[ "${DRY_RUN}" -eq 0 ]]; then
  require_bin curl
  require_bin jq
  if [[ -z "${BASE_URL}" ]]; then
    echo "[validate-rollout] BASE_URL/RELEASE_VALIDATION_BASE_URL is required" >&2
    exit "${EXIT_CONFIG}"
  fi
  if [[ -z "${ADMIN_KEY}" ]]; then
    echo "[validate-rollout] ADMIN_API_KEY (or --admin-key) is required" >&2
    exit "${EXIT_CONFIG}"
  fi
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  cat <<EOF
[validate-rollout] dry-run plan
- BASE_URL: ${BASE_URL:-<missing>}
- FEATURE_KEY: ${FEATURE_KEY}
- ENVIRONMENT: ${ENVIRONMENT}
- MANUSCRIPT_ID: ${MANUSCRIPT_ID:-<not-set>}
- READINESS_ONLY: ${READINESS_ONLY}
- STRICT_BLOCKING: ${STRICT_BLOCKING}
- REQUIRE_ZERO_SKIP: ${REQUIRE_ZERO_SKIP}
- FORCE_NO_GO: ${FORCE_NO_GO}
- steps:
  1) POST /internal/release-validation/runs
  2) POST /internal/release-validation/runs/{run_id}/readiness
  3) POST /internal/release-validation/runs/{run_id}/regression (unless readiness-only)
  4) POST /internal/release-validation/runs/{run_id}/finalize (unless readiness-only)
  5) GET  /internal/release-validation/runs/{run_id}/report (unless readiness-only)
EOF
  exit "${EXIT_OK}"
fi

STRICT_BLOCKING_JSON="$(normalize_bool "${STRICT_BLOCKING}")"
REQUIRE_ZERO_SKIP_JSON="$(normalize_bool "${REQUIRE_ZERO_SKIP}")"
NO_GO=0

echo "[validate-rollout] creating validation run..."
CREATE_PAYLOAD="$(
  jq -nc \
    --arg feature_key "${FEATURE_KEY}" \
    --arg environment "${ENVIRONMENT}" \
    --arg manuscript_id "${MANUSCRIPT_ID}" \
    '{
      feature_key: $feature_key,
      environment: $environment
    } + (if ($manuscript_id | length) > 0 then {manuscript_id: $manuscript_id} else {} end)'
)"
request_json POST "/internal/release-validation/runs" "${CREATE_PAYLOAD}"
if [[ "${HTTP_STATUS}" -ge 400 ]]; then
  echo "[validate-rollout] create run failed: HTTP ${HTTP_STATUS}" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi

RUN_ID="$(echo "${HTTP_BODY}" | jq -er '.run.id')"
if [[ -z "${RUN_ID}" ]]; then
  echo "[validate-rollout] create run response missing run.id" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi
echo "[validate-rollout] run_id=${RUN_ID}"

echo "[validate-rollout] executing readiness..."
READINESS_PAYLOAD="$(jq -nc --argjson strict_blocking "${STRICT_BLOCKING_JSON}" '{strict_blocking: $strict_blocking}')"
request_json POST "/internal/release-validation/runs/${RUN_ID}/readiness" "${READINESS_PAYLOAD}"
if [[ "${HTTP_STATUS}" -ge 400 ]]; then
  echo "[validate-rollout] readiness failed: HTTP ${HTTP_STATUS}" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi

READINESS_STATUS="$(echo "${HTTP_BODY}" | jq -er '.result.status')"
READINESS_BLOCKING_COUNT="$(echo "${HTTP_BODY}" | jq '[.result.checks[]? | select(.is_blocking == true and (.status == "failed" or .status == "blocked"))] | length')"
READINESS_SKIPPED_COUNT="$(echo "${HTTP_BODY}" | jq '[.result.checks[]? | select(.status == "skipped")] | length')"
READINESS_NOT_PASSED="$(echo "${HTTP_BODY}" | jq -c '[.result.checks[]? | select(.status != "passed") | {key: .check_key, status: .status, blocking: .is_blocking, detail: .detail}]')"
echo "[validate-rollout] readiness status=${READINESS_STATUS} blocking=${READINESS_BLOCKING_COUNT} skipped=${READINESS_SKIPPED_COUNT}"
if [[ "${READINESS_STATUS}" != "passed" ]]; then
  echo "[validate-rollout] readiness non-passed checks=${READINESS_NOT_PASSED}"
  NO_GO=1
fi

if [[ "${READINESS_ONLY}" -eq 1 ]]; then
  if [[ "${NO_GO}" -eq 1 ]]; then
    echo "[validate-rollout] readiness-only result: NO-GO"
    exit "${EXIT_NO_GO}"
  fi
  echo "[validate-rollout] readiness-only result: GO"
  exit "${EXIT_OK}"
fi

echo "[validate-rollout] executing regression..."
REGRESSION_PAYLOAD="$(jq -nc --argjson require_zero_skip "${REQUIRE_ZERO_SKIP_JSON}" '{require_zero_skip: $require_zero_skip}')"
request_json POST "/internal/release-validation/runs/${RUN_ID}/regression" "${REGRESSION_PAYLOAD}"
if [[ "${HTTP_STATUS}" -ge 400 ]]; then
  echo "[validate-rollout] regression failed: HTTP ${HTTP_STATUS}" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi

REGRESSION_STATUS="$(echo "${HTTP_BODY}" | jq -er '.result.status')"
REGRESSION_SKIP_COUNT="$(echo "${HTTP_BODY}" | jq '[.result.checks[]? | select(.status == "skipped")] | length')"
echo "[validate-rollout] regression status=${REGRESSION_STATUS} skipped=${REGRESSION_SKIP_COUNT}"
if [[ "${REGRESSION_STATUS}" != "passed" ]]; then
  NO_GO=1
fi
if [[ "${REQUIRE_ZERO_SKIP_JSON}" == "true" && "${REGRESSION_SKIP_COUNT}" -gt 0 ]]; then
  NO_GO=1
fi

if [[ "${FORCE_NO_GO}" -eq 1 ]]; then
  NO_GO=1
fi

echo "[validate-rollout] finalizing..."
FORCE_NO_GO_JSON="false"
if [[ "${NO_GO}" -eq 1 ]]; then
  FORCE_NO_GO_JSON="true"
fi
FINALIZE_PAYLOAD="$(jq -nc --argjson force_no_go "${FORCE_NO_GO_JSON}" '{force_no_go: $force_no_go}')"
request_json POST "/internal/release-validation/runs/${RUN_ID}/finalize" "${FINALIZE_PAYLOAD}"
if [[ "${HTTP_STATUS}" -ge 400 ]]; then
  echo "[validate-rollout] finalize failed: HTTP ${HTTP_STATUS}" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi

RELEASE_DECISION="$(echo "${HTTP_BODY}" | jq -er '.release_decision')"
echo "[validate-rollout] release_decision=${RELEASE_DECISION}"
if [[ "${RELEASE_DECISION}" != "go" ]]; then
  NO_GO=1
fi

echo "[validate-rollout] fetching report..."
request_json GET "/internal/release-validation/runs/${RUN_ID}/report"
if [[ "${HTTP_STATUS}" -ge 400 ]]; then
  echo "[validate-rollout] report fetch failed: HTTP ${HTTP_STATUS}" >&2
  echo "${HTTP_BODY}" >&2
  exit "${EXIT_RUNTIME}"
fi

RUN_STATUS="$(echo "${HTTP_BODY}" | jq -r '.run.status // "unknown"')"
BLOCKING_COUNT="$(echo "${HTTP_BODY}" | jq -r '.run.blocking_count // 0')"
FAILED_COUNT="$(echo "${HTTP_BODY}" | jq -r '.run.failed_count // 0')"
SKIPPED_COUNT="$(echo "${HTTP_BODY}" | jq -r '.run.skipped_count // 0')"
ROLLBACK_REQUIRED="$(echo "${HTTP_BODY}" | jq -r '.rollback_plan.required // false')"
echo "[validate-rollout] report summary: run_status=${RUN_STATUS} blocking=${BLOCKING_COUNT} failed=${FAILED_COUNT} skipped=${SKIPPED_COUNT} rollback_required=${ROLLBACK_REQUIRED}"

if [[ "${NO_GO}" -eq 1 ]]; then
  echo "[validate-rollout] result: NO-GO"
  if [[ "${ROLLBACK_REQUIRED}" == "true" ]]; then
    echo "[validate-rollout] rollback required, check report.rollback_plan.steps"
  fi
  exit "${EXIT_NO_GO}"
fi

echo "[validate-rollout] result: GO"
exit "${EXIT_OK}"
