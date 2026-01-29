@echo off
:: ScholarFlow 一键启动脚本 (Windows)

echo 🚀 Starting ScholarFlow...

:: 1. 加载环境变量 (优先根目录 .env，其次 backend\.env)
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)
if exist backend\.env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("backend\\.env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

:: 2. 启动后端
echo 🐍 Starting Backend (FastAPI on :8000)...
start "ScholarFlow Backend" cmd /k "cd backend && call .venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000"

:: 3. 启动前端
echo ⚛️  Starting Frontend (Next.js on :3000)...
start "ScholarFlow Frontend" cmd /k "cd frontend && set NODE_OPTIONS=--dns-result-order=ipv4first && pnpm dev"

echo ✅ ScholarFlow launched in new windows!
echo 👉 Frontend: http://localhost:3000
echo 👉 Backend:  http://localhost:8000/docs
pause
