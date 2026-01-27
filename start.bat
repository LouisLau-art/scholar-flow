@echo off
:: ScholarFlow 一键启动脚本 (Windows)

echo 🚀 Starting ScholarFlow...

:: 1. 启动后端
echo 🐍 Starting Backend (FastAPI on :8000)...
start "ScholarFlow Backend" cmd /k "cd backend && call .venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: 2. 启动前端
echo ⚛️  Starting Frontend (Next.js on :3000)...
start "ScholarFlow Frontend" cmd /k "cd frontend && pnpm dev"

echo ✅ ScholarFlow launched in new windows!
echo 👉 Frontend: http://localhost:3000
echo 👉 Backend:  http://localhost:8000/docs
pause
