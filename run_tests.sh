#!/bin/bash

# ScholarFlow 全量自动化测试脚本
# 功能: 一键运行前后端测试并输出报告

echo "🛡️ Starting ScholarFlow Quality Shield..."

# 1. 后端测试
echo "🐍 Running Backend Tests (pytest)..."
cd backend
export PYTHONPATH=$PYTHONPATH:.
pytest tests/ -v
BACKEND_STATUS=$?
cd ..

echo "-----------------------------------"

# 2. 前端测试
echo "⚛️  Running Frontend Tests (vitest)..."
cd frontend
pnpm vitest run
FRONTEND_STATUS=$?
cd ..

echo "-----------------------------------"

if [ $BACKEND_STATUS -eq 0 ] && [ $FRONTEND_STATUS -eq 0 ]; then
    echo "✅ ALL TESTS PASSED! The system is stable."
    exit 0
else
    echo "❌ SOME TESTS FAILED. Please check the logs above."
    exit 1
fi
