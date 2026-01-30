#!/bin/bash

# ScholarFlow 一键启动脚本
# 功能: 加载环境变量 -> 启动后端 (8000) -> 启动前端 (3000)

echo "🚀 Starting ScholarFlow..."

# 1. 加载环境变量 (优先根目录 .env，其次 backend/.env)
# 注：使用 source 以支持带引号/特殊字符的值
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
pkill -f "next-server" || true

# 3. 启动后端 (后台运行)
echo "🐍 Starting Backend (FastAPI on :8000)..."
BACKEND_RELOAD="${BACKEND_RELOAD:-0}"
BACKEND_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"
if [ "$BACKEND_RELOAD" = "1" ]; then
  BACKEND_CMD="$BACKEND_CMD --reload"
fi
nohup bash -lc "cd backend && $BACKEND_CMD" > backend/backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端就绪（最多 10 秒）
for i in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:8000/docs" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# 4. 启动前端 (前台运行，以便查看输出)
echo "⚛️  Starting Frontend (Next.js on :3000)..."
NODE_OPTIONS="${NODE_OPTIONS:-} --dns-result-order=ipv4first"
export NODE_OPTIONS
nohup bash -lc "cd frontend && HOSTNAME=0.0.0.0 pnpm dev" > frontend.log 2>&1 &
FRONTEND_PID=$!

echo "✅ ScholarFlow is running!"
echo "👉 Frontend: http://localhost:3000"
echo "👉 Backend:  http://localhost:8000/docs"
echo "Press Ctrl+C to stop both services."

# 5. 捕获退出信号，同时关闭前后端
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
