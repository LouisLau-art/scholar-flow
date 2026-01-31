#!/usr/bin/env bash
set -euo pipefail

# Feature 016: 验证 reset-db / seed-db 内部接口可用性（T010）
#
# 依赖：
# - 后端已启动（默认 http://localhost:8000）
# - 后端环境已开启 ENABLE_TEST_ENDPOINTS=true（或 GO_ENV/ENV=test|dev）
# - 已设置 ADMIN_API_KEY（作为 Bearer token）

BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
TOKEN="${ADMIN_API_KEY:-}"

if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: ADMIN_API_KEY 未设置（用于 Authorization: Bearer ...）" >&2
  exit 1
fi

echo "POST ${BASE_URL}/api/v1/internal/reset-db"
curl -fsS -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/api/v1/internal/reset-db" | cat
echo

echo "POST ${BASE_URL}/api/v1/internal/seed-db"
curl -fsS -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/api/v1/internal/seed-db" | cat
echo

echo "OK"

