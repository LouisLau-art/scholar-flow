#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-${UAT_BASE_URL:-}}"
EXPECTED_SHA="${EXPECTED_SHA:-}"
WAIT_ATTEMPTS="${FRONTEND_SHA_WAIT_ATTEMPTS:-30}"
WAIT_SECONDS="${FRONTEND_SHA_WAIT_SECONDS:-10}"

usage() {
  cat <<'EOF'
Usage: scripts/ci/check-frontend-runtime.sh [options]

Options:
  --base-url <url>       Frontend base URL, e.g. https://scholar-flow-q1yw.vercel.app
  --expected-sha <sha>   Expected deployed frontend commit SHA
  -h, --help             Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --expected-sha)
      EXPECTED_SHA="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[frontend-runtime] unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${BASE_URL}" ]]; then
  echo "[frontend-runtime] BASE_URL/UAT_BASE_URL is required" >&2
  exit 2
fi

if [[ -z "${EXPECTED_SHA}" ]]; then
  echo "[frontend-runtime] EXPECTED_SHA/--expected-sha is required" >&2
  exit 2
fi

runtime_sha="-"
body="{}"
http_status="000"
for attempt in $(seq 1 "${WAIT_ATTEMPTS}"); do
  tmp_file="$(mktemp)"
  http_status="$(
    curl -sS -o "${tmp_file}" -w "%{http_code}" \
      "${BASE_URL}/api/internal/runtime-version" || true
  )"
  body="$(cat "${tmp_file}")"
  rm -f "${tmp_file}"

  if [[ "${http_status}" == "200" ]]; then
    runtime_sha="$(echo "${body}" | jq -er '.deploy_sha // "-"')"
    echo "[frontend-runtime] runtime_sha=${runtime_sha} expected=${EXPECTED_SHA} attempt=${attempt}/${WAIT_ATTEMPTS}"
    if [[ "${runtime_sha}" == "${EXPECTED_SHA}" ]]; then
      break
    fi
  else
    echo "[frontend-runtime] status=${http_status} attempt=${attempt}/${WAIT_ATTEMPTS}"
  fi

  if [[ "${attempt}" -lt "${WAIT_ATTEMPTS}" ]]; then
    sleep "${WAIT_SECONDS}"
  fi
done

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  pretty_body="$(printf '%s' "${body}" | jq '.' 2>/dev/null || printf '%s' "${body}")"
  {
    echo "## Frontend Runtime"
    echo
    echo "- Base URL: \`${BASE_URL}\`"
    echo "- Expected SHA: \`${EXPECTED_SHA}\`"
    echo "- Runtime SHA: \`${runtime_sha}\`"
    echo "- Last HTTP Status: \`${http_status}\`"
    echo
    echo '```'
    printf '%s\n' "${pretty_body}"
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
fi

if [[ "${http_status}" -ge 400 ]]; then
  echo "[frontend-runtime] runtime endpoint failed: HTTP ${http_status}" >&2
  echo "${body}" >&2
  exit 1
fi

if [[ "${runtime_sha}" != "${EXPECTED_SHA}" ]]; then
  echo "[frontend-runtime] deployed frontend SHA did not converge to expected SHA" >&2
  exit 1
fi
