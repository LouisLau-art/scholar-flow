#!/bin/bash

# 显示覆盖率摘要
# 用法: ./scripts/coverage/summary.sh

set -e

echo "📊 测试覆盖率摘要"
echo "=================="
echo ""

# 检查后端覆盖率
if [ -f "backend/coverage.xml" ]; then
    echo "后端覆盖率:"
    echo "  - XML报告: backend/coverage.xml"
    echo "  - HTML报告: backend/htmlcov/index.html"
    echo ""
else
    echo "后端覆盖率报告未生成"
    echo "运行: cd backend && pytest --cov=src --cov-report=xml --cov-report=html"
    echo ""
fi

# 检查前端覆盖率
if [ -f "frontend/coverage/coverage-summary.json" ]; then
    echo "前端覆盖率:"
    echo "  - JSON报告: frontend/coverage/coverage-summary.json"
    echo "  - HTML报告: frontend/coverage/index.html"
    echo ""
elif [ -f "frontend/coverage/coverage-final.json" ]; then
    echo "前端覆盖率:"
    echo "  - JSON报告: frontend/coverage/coverage-final.json"
    echo "  - HTML报告: frontend/coverage/index.html"
    echo ""
else
    echo "前端覆盖率报告未生成"
    echo "运行: cd frontend && bun run test:coverage"
    echo ""
fi

echo "目标覆盖率:"
echo "  - 后端: >80% (行覆盖率 + 分支覆盖率)"
echo "  - 前端: >70% (行覆盖率 + 分支覆盖率)"
echo "  - 关键业务逻辑: 100%"
