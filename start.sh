#!/bin/bash

# ScholarFlow 一键启动脚本
# 功能: 加载环境变量 -> 启动后端 (8000) -> 启动前端 (3000)

# 日志目标：
# 1) 终端实时可见（stdout）
# 2) 同步持久化到 logs/ 下的文件（便于排查/AI Agent 阅读）

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

# 1.5 Hugging Face / sentence-transformers 本地缓存（解决“每次推荐都去 HF 下载/很慢”）
# 中文注释:
# - 默认把缓存放到 repo 下的 .cache/，便于“下载一次、后续复用”，也方便你清理。
# - 国内网络可选设置：HF_ENDPOINT=https://hf-mirror.com（只要在终端 export 或写入 .env 即可）。
ROOT_DIR="$(pwd)"
export HF_HOME="${HF_HOME:-$ROOT_DIR/.cache/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
export SENTENCE_TRANSFORMERS_HOME="${SENTENCE_TRANSFORMERS_HOME:-$HF_HOME/sentence-transformers}"
mkdir -p "$HF_HOME" "$HF_HUB_CACHE" "$TRANSFORMERS_CACHE" "$SENTENCE_TRANSFORMERS_HOME" 2>/dev/null || true

# 可选：启动后端时后台预热模型，避免 Editor 第一次点“Assign Reviewer”卡 20s+（默认开启）
export MATCHMAKING_WARMUP="${MATCHMAKING_WARMUP:-1}"

# 2. 清理旧进程 (防止端口冲突)
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn main:app" || true
pkill -f "next dev" || true

# 2.5 准备日志目录与文件（每次启动生成独立文件，并让 logs/backend.log 指向“最新一次”）
mkdir -p logs
TS="$(date +%Y%m%d-%H%M%S)"
BACKEND_LOG="logs/backend-${TS}.log"
FRONTEND_LOG="logs/frontend-${TS}.log"
ln -sf "$(basename "$BACKEND_LOG")" logs/backend.log
ln -sf "$(basename "$FRONTEND_LOG")" logs/frontend.log

echo "📝 Logs:"
echo "   - Backend:  $BACKEND_LOG (alias: logs/backend.log)"
echo "   - Frontend: $FRONTEND_LOG (alias: logs/frontend.log)"

# 3. 启动后端 (后台运行，保留颜色和输出)
echo -e "${GREEN}🐍 Starting Backend (FastAPI on :8000)...${NC}"
(
  cd backend || exit 1
  # 使用 --reload 启用热重载，便于开发
  # PYTHONUNBUFFERED=1 确保日志实时 flush
  PYTHONUNBUFFERED=1 uvicorn main:app --host 0.0.0.0 --port 8000 --reload 2>&1 \
    | stdbuf -oL -eL tee -a "../$BACKEND_LOG"
) &
BACKEND_TEE_PID=$!

# 4. 启动前端 (后台运行，保留颜色和输出)
echo -e "${GREEN}⚛️  Starting Frontend (Next.js on :3000)...${NC}"
(
  cd frontend || exit 1
  # 确保 pnpm dev 的输出包含颜色
  FORCE_COLOR=1 pnpm dev 2>&1 | stdbuf -oL -eL tee -a "../$FRONTEND_LOG"
) &
FRONTEND_TEE_PID=$!

echo -e "${GREEN}✅ ScholarFlow is running!${NC}"
echo -e "👉 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "👉 Backend:  ${BLUE}http://localhost:8000/docs${NC}"
echo "Press Ctrl+C to stop both services."
echo "---------------------------------------------------"

# 5. 捕获退出信号，同时关闭前后端
cleanup() {
  echo
  echo "🛑 Stopping ScholarFlow..."
  # 先杀真实服务进程（reload/child 也一并处理）
  pkill -f "uvicorn main:app" || true
  pkill -f "next dev" || true
  pkill -f "pnpm dev" || true
  # 再杀 tee 管道（避免残留后台输出）
  kill "$BACKEND_TEE_PID" 2>/dev/null || true
  kill "$FRONTEND_TEE_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# 等待所有子进程
wait
