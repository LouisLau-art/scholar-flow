#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-${UAT_API_BASE_URL:-}}"
ADMIN_KEY="${ADMIN_API_KEY:-}"

usage() {
  cat <<'EOF'
Usage: scripts/ci/check-platform-readiness.sh [options]

Options:
  --base-url <url>   Backend base URL, e.g. https://xxx.hf.space
  --admin-key <key>  ADMIN_API_KEY for internal endpoint
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
