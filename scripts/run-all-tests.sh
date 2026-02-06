#!/bin/bash

# 运行所有测试（后端 + 前端）
# 用法: ./scripts/run-all-tests.sh

set -e

echo "🧪 运行所有测试"
echo "==============="
echo ""

# 尝试加载根目录 .env（仅在未设置关键变量时），便于本地一键跑通
if [ -z "${SUPABASE_URL:-}" ] && [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ".env"
    set +a
fi

if [ -z "${SUPABASE_URL:-}" ]; then
    echo "⚠️  警告: SUPABASE_URL 未设置（部分真实 DB 集成测试可能跳过）"
    echo ""
fi

if [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ] && [ -z "${SUPABASE_KEY:-}" ] && [ -z "${SUPABASE_ANON_KEY:-}" ]; then
    echo "⚠️  警告: SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY/SUPABASE_ANON_KEY 均未设置（部分真实 DB 集成测试可能跳过）"
    echo ""
fi

echo "1️⃣  运行后端测试..."
echo "-------------------"
cd backend

# 安装依赖（如果需要）
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "📦 安装后端测试依赖..."
    uv pip install --system -r requirements.txt
    uv pip install --system -r requirements-dev.txt
fi

# 运行测试
echo "🧪 执行 pytest..."
CI=1 pytest -v --tb=short --cov=app --cov-report=xml --cov-report=html --cov-report=term-missing

cd ..

echo ""
echo "2️⃣  运行前端单元测试..."
echo "------------------------"
cd frontend

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    bun install
fi

# 运行测试
echo "🧪 执行 Vitest..."
bun run test:run

echo ""
echo "3️⃣  运行前端 E2E 测试（Playwright/Chromium）..."
echo "-----------------------------------------------"
# 默认从 3100 起找空闲端口，避免误复用其他项目的 dev server（Nuxt/Next 等）。
# 可通过 PLAYWRIGHT_PORT 覆盖。
if [ -z "${PLAYWRIGHT_PORT:-}" ]; then
    for p in $(seq 3100 3199); do
        if ! ss -ltn "sport = :$p" 2>/dev/null | tail -n +2 | grep -q LISTEN; then
            export PLAYWRIGHT_PORT="$p"
            break
        fi
    done
fi
export PLAYWRIGHT_PORT="${PLAYWRIGHT_PORT:-3100}"

# 默认只跑“可脱离真实后端”的 mocked E2E（更接近 CI 可重复性）。
# 若你希望跑全量 E2E（可能依赖后端 HTTP 服务 / 真实 Supabase），设置 E2E_FULL=1。
E2E_FULL="${E2E_FULL:-0}"
E2E_SPEC="${E2E_SPEC:-tests/e2e/specs/*.spec.ts}"

if [ "$E2E_FULL" = "1" ]; then
    echo "ℹ️  E2E_FULL=1：尝试启动后端 (127.0.0.1:${BACKEND_PORT:-8000}) 并运行全量 Playwright 用例"

    BACKEND_PORT="${BACKEND_PORT:-8000}"
    if python3 -c "import uvicorn" 2>/dev/null; then
        (
            cd ../backend
            uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" > /tmp/scholarflow-backend-e2e.log 2>&1 &
            echo $! > /tmp/scholarflow-backend-e2e.pid
        )
        BACKEND_PID="$(cat /tmp/scholarflow-backend-e2e.pid)"
        trap 'kill -TERM "$BACKEND_PID" 2>/dev/null || true' EXIT
    else
        echo "❌ 未检测到 uvicorn，无法自动启动后端；请手动启动后再重试：cd backend && uvicorn main:app --port ${BACKEND_PORT:-8000}"
        exit 1
    fi

    CI=1 bunx playwright test --project=chromium
else
    echo "ℹ️  默认仅跑：$E2E_SPEC（mocked backend）"
    echo "ℹ️  启动本地 mock backend (127.0.0.1:8000) 兜底 /api/v1/*，避免 Next rewrites 触发 ECONNREFUSED"

    python3 ../scripts/mock_backend_server.py --host 127.0.0.1 --port 8000 > /tmp/scholarflow-mock-backend.log 2>&1 &
    MOCK_BACKEND_PID="$!"
    trap 'kill -TERM "$MOCK_BACKEND_PID" 2>/dev/null || true' EXIT

    # 中文注释：允许使用 glob（默认 tests/e2e/specs/*.spec.ts），不要把参数整体 quote 掉，否则 Playwright 找不到文件。
    # shellcheck disable=SC2086
    CI=1 bunx playwright test $E2E_SPEC --project=chromium
fi

cd ..

echo ""
echo "✅ 所有测试完成！"
echo ""
echo "📊 生成覆盖率报告..."
echo "  运行: ./scripts/coverage/generate-report.sh"
