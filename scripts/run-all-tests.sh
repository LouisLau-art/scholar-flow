#!/bin/bash

# 运行所有测试（后端 + 前端）
# 用法: ./scripts/run-all-tests.sh

set -e

echo "🧪 运行所有测试"
echo "==============="
echo ""

# 检查环境变量
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "⚠️  警告: SUPABASE_URL 和 SUPABASE_KEY 未设置"
    echo "    集成测试将跳过"
    echo ""
fi

echo "1️⃣  运行后端测试..."
echo "-------------------"
cd backend

# 安装依赖（如果需要）
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "📦 安装后端测试依赖..."
    pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt
fi

# 运行测试
echo "🧪 执行 pytest..."
pytest -v --tb=short

cd ..

echo ""
echo "2️⃣  运行前端单元测试..."
echo "------------------------"
cd frontend

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 运行测试
echo "🧪 执行 Vitest..."
npm run test:run

cd ..

echo ""
echo "✅ 所有测试完成！"
echo ""
echo "📊 生成覆盖率报告..."
echo "  运行: ./scripts/coverage/generate-report.sh"
