#!/bin/bash

# ScholarFlow 一键启动脚本
# 功能: 加载环境变量 -> 启动后端 (8000) -> 启动前端 (3000)

echo "🚀 Starting ScholarFlow..."

# 1. 加载后端环境变量 (如果存在)
if [ -f backend/.env ]; then
    echo "📄 Loading backend environment variables..."
    export $(grep -v '^#' backend/.env | xargs)
fi

# 2. 清理旧进程 (防止端口冲突)
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn main:app" || true
pkill -f "next-server" || true

# 3. 启动后端 (后台运行)
echo "🐍 Starting Backend (FastAPI on :8000)..."
cd backend
nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# 等待几秒确保后端初始化
sleep 2

# 4. 启动前端 (前台运行，以便查看输出)
echo "⚛️  Starting Frontend (Next.js on :3000)..."
cd frontend
# 使用 HOSTNAME 环境变量指定监听 IP，避免 next dev 参数解析错误
# 开启 --turbo (Turbopack) 加速编译
HOSTNAME=0.0.0.0 pnpm dev --turbo &
FRONTEND_PID=$!
cd ..

echo "✅ ScholarFlow is running!"
echo "👉 Frontend: http://localhost:3000"
echo "👉 Backend:  http://localhost:8000/docs"
echo "Press Ctrl+C to stop both services."

# 5. 捕获退出信号，同时关闭前后端
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
