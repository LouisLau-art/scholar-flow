#!/bin/bash

# Tier-1 快速回归测试（提速默认）
# - 后端：仅跑 unit，并显式禁用全局 addopts（避免覆盖率门槛拖慢迭代）
# - 前端：跑 Vitest（不含 Playwright）
#
# 可选：
# - BACKEND_TESTS="tests/integration/test_user_profile.py::test_update_profile_success"
# - FRONTEND_TESTS="src/tests/SubmissionForm.test.tsx"
#
# 用法：
#   ./scripts/test-fast.sh
#   BACKEND_TESTS="tests/integration/test_error_handling.py::test_upload_internal_error" ./scripts/test-fast.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "⚡ Tier-1 快速回归"
echo "================="

echo ""
echo "1) Backend (pytest -m unit, no global addopts)"
echo "---------------------------------------------"
cd "$ROOT_DIR/backend"

BACKEND_TESTS="${BACKEND_TESTS:-}"
if [ -n "$BACKEND_TESTS" ]; then
  pytest -q -o addopts= "$BACKEND_TESTS"
else
  pytest -q -o addopts= -m unit
fi

echo ""
echo "2) Frontend (vitest run)"
echo "------------------------"
cd "$ROOT_DIR/frontend"

FRONTEND_TESTS="${FRONTEND_TESTS:-}"
if [ -n "$FRONTEND_TESTS" ]; then
  bun run test:run -- "$FRONTEND_TESTS"
else
  bun run test:run
fi

echo ""
echo "✅ Tier-1 完成"
