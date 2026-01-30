#!/bin/bash

# ScholarFlow 生产模式启动脚本
# 功能: 构建并启动优化后的生产版本 (速度极快)

echo "🚀 Preparing ScholarFlow Production Build..."

# 1. 加载环境变量
if [ -f backend/.env ]; then
    echo "📄 Loading backend environment variables..."
    export $(grep -v '^#' backend/.env | xargs)
fi

# 2. 清理旧进程
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn main:app" || true
pkill -f "next-server" || true
pkill -f "next start" || true

# 3. 启动后端 (依然使用 uvicorn，但生产模式推荐多 Worker)
echo "🐍 Starting Backend (FastAPI Production Mode)..."
cd backend
# 使用 4 个 Workers 提升并发能力
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > backend_prod.log 2>&1 &
BACKEND_PID=$!
cd ..

# 4. 构建并启动前端
echo "⚛️  Building Frontend (This may take a minute, but runs fast later)..."
cd frontend
# 显式设置 CI=true 避免 build 时的 lint 警告阻断
CI=true pnpm build

echo "⚡ Starting Frontend (Next.js Production Mode)..."
# 生产模式启动，绑定 0.0.0.0
HOSTNAME=0.0.0.0 pnpm start -p 3000 &
FRONTEND_PID=$!
cd ..

echo "✅ ScholarFlow Production is LIVE!"
echo "👉 Frontend: http://localhost:3000 (Blazing Fast!)"
echo "👉 Backend:  http://localhost:8000/docs"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
