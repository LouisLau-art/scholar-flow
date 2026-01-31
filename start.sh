#!/bin/bash

# ScholarFlow 一键启动脚本
# 功能: 加载环境变量 -> 启动后端 (8000) -> 启动前端 (3000)

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting ScholarFlow...${NC}"

# 1. 加载环境变量 (优先根目录 .env，其次 backend/.env)
if [ -f .env ]; then
  echo "📄 Loading root environment variables..."
  set -a
  source .env
  set +a
fi
if [ -f backend/.env ]; then
  echo "📄 Loading backend environment variables..."
  set -a
  source backend/.env
  set +a
fi

# 2. 清理旧进程 (防止端口冲突)
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn main:app" || true
pkill -f "next dev" || true

# 3. 启动后端 (后台运行，保留颜色和输出)
echo -e "${GREEN}🐍 Starting Backend (FastAPI on :8000)...${NC}"
cd backend
# 使用 --reload 启用热重载，便于开发
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 4. 启动前端 (后台运行，保留颜色和输出)
echo -e "${GREEN}⚛️  Starting Frontend (Next.js on :3000)...${NC}"
cd frontend
# 确保 pnpm dev 的输出包含颜色
FORCE_COLOR=1 pnpm dev &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ ScholarFlow is running!${NC}"
echo -e "👉 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "👉 Backend:  ${BLUE}http://localhost:8000/docs${NC}"
echo "Press Ctrl+C to stop both services."
echo "---------------------------------------------------"

# 5. 捕获退出信号，同时关闭前后端
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT

# 等待所有子进程
wait