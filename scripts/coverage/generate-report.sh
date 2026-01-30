#!/bin/bash

# 生成测试覆盖率报告
# 用法: ./scripts/coverage/generate-report.sh

set -e

echo "🚀 生成测试覆盖率报告..."

# 进入后端目录
cd backend

echo "📦 安装测试依赖..."
pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt

echo "🧪 运行后端测试并生成覆盖率报告..."
pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing

echo "📊 后端覆盖率报告已生成: backend/htmlcov/index.html"

# 返回项目根目录
cd ..

# 进入前端目录
cd frontend

echo "📦 安装前端依赖..."
npm install

echo "🧪 运行前端单元测试并生成覆盖率报告..."
npm run test:coverage

echo "📊 前端覆盖率报告已生成: frontend/coverage/index.html"

# 返回项目根目录
cd ..

echo ""
echo "✅ 覆盖率报告生成完成！"
echo ""
echo "后端报告: backend/htmlcov/index.html"
echo "前端报告: frontend/coverage/index.html"
echo ""
echo "查看报告:"
echo "  - 后端: open backend/htmlcov/index.html"
echo "  - 前端: open frontend/coverage/index.html"
