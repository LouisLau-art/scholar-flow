#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${FRONTEND_ROOT}"

failures=0

run_check() {
  local name="$1"
  local cmd="$2"
  echo "[audit] ${name}"
  local output
  output="$(eval "${cmd}" || true)"
  if [[ -n "${output}" ]]; then
    echo "  FAIL"
    echo "${output}" | sed 's/^/    /'
    failures=1
  else
    echo "  PASS"
  fi
}

run_check \
  "禁止占位链接 href=\"#\"" \
  "rg -n 'href=\"#\"' src"

run_check \
  "禁止非语义节点伪点击 (div/li/span + cursor-pointer)" \
  "rg -n '<(div|li|span)[^>]*cursor-pointer' src"

run_check \
  "加载文案统一省略号（禁止三个点 ...）" \
  "rg -n 'Loading\\.\\.\\.|Submitting\\.\\.\\.|Confirming\\.\\.\\.|Removing\\.\\.\\.' src"

run_check \
  "目标组件禁止散落 date-fns format（应统一走 date-display）" \
  "rg -n \"from ['\\\"]date-fns['\\\"]\" \
    src/components/editor/ManuscriptTable.tsx \
    src/components/editor/InternalNotebook.tsx \
    src/components/editor/AuditLogTimeline.tsx \
    src/components/finance/FinanceInvoicesTable.tsx \
    'src/app/(admin)/admin/feedback/_components/FeedbackTable.tsx'"

if [[ "${failures}" -ne 0 ]]; then
  echo
  echo "UI guideline audit failed."
  exit 1
fi

echo
echo "UI guideline audit passed."
