#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-${UAT_API_BASE_URL:-}}"
ADMIN_KEY="${ADMIN_API_KEY:-}"
EXPECTED_DEPLOY_SHA="${EXPECTED_DEPLOY_SHA:-}"

usage() {
  cat <<'EOF'
Usage: scripts/ci/check-platform-readiness.sh [options]

Options:
  --base-url <url>   Backend base URL, e.g. https://xxx.hf.space
  --admin-key <key>  ADMIN_API_KEY for internal endpoint
  --expected-deploy-sha <sha>  Fail if /internal/runtime-version does not match
  -h, --help         Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --admin-key)
      ADMIN_KEY="${2:-}"
      shift 2
      ;;
    --expected-deploy-sha)
      EXPECTED_DEPLOY_SHA="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[platform-readiness] unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${BASE_URL}" ]]; then
  echo "[platform-readiness] BASE_URL/UAT_API_BASE_URL is required" >&2
  exit 2
fi

if [[ -z "${ADMIN_KEY}" ]]; then
  echo "[platform-readiness] ADMIN_API_KEY/--admin-key is required" >&2
  exit 2
fi

tmp_file="$(mktemp)"
http_status="$(
  curl -sS -o "${tmp_file}" -w "%{http_code}" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    "${BASE_URL}/api/v1/internal/platform-readiness"
)"
body="$(cat "${tmp_file}")"
rm -f "${tmp_file}"

if [[ "${http_status}" -ge 400 ]]; then
  echo "[platform-readiness] request failed: HTTP ${http_status}" >&2
  echo "${body}" >&2
  exit 3
fi

status="$(echo "${body}" | jq -er '.status')"
echo "[platform-readiness] status=${status}"
echo "${body}" | jq '.'

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## Platform Readiness"
    echo
    echo "- Base URL: \`${BASE_URL}\`"
    echo "- Status: **${status}**"
    echo
    echo '```json'
    echo "${body}" | jq '.'
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
fi

if [[ "${status}" != "passed" ]]; then
  echo "[platform-readiness] blocking readiness issue detected" >&2
  exit 1
fi

runtime_sha="-"
if [[ -n "${EXPECTED_DEPLOY_SHA}" ]]; then
  runtime_tmp_file="$(mktemp)"
  runtime_http_status="$(
    curl -sS -o "${runtime_tmp_file}" -w "%{http_code}" \
      -H "X-Admin-Key: ${ADMIN_KEY}" \
      "${BASE_URL}/api/v1/internal/runtime-version"
  )"
  runtime_body="$(cat "${runtime_tmp_file}")"
  rm -f "${runtime_tmp_file}"

  if [[ "${runtime_http_status}" -ge 400 ]]; then
    echo "[platform-readiness] runtime version request failed: HTTP ${runtime_http_status}" >&2
    echo "${runtime_body}" >&2
    exit 4
  fi

  runtime_sha="$(echo "${runtime_body}" | jq -er '.deploy_sha // "-"')"
  echo "[platform-readiness] runtime_sha=${runtime_sha} expected=${EXPECTED_DEPLOY_SHA}"

  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo
      echo "### Runtime Version"
      echo
      echo "- Expected Deploy SHA: \`${EXPECTED_DEPLOY_SHA}\`"
      echo "- Runtime Deploy SHA: \`${runtime_sha}\`"
    } >> "${GITHUB_STEP_SUMMARY}"
  fi

  if [[ "${runtime_sha}" != "${EXPECTED_DEPLOY_SHA}" ]]; then
    echo "[platform-readiness] runtime DEPLOY_SHA does not match expected SHA" >&2
    exit 5
  fi
fi
