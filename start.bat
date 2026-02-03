@echo off
:: ScholarFlow 一键启动脚本 (Windows)
:: 功能: 清理进程 -> 加载环境变量 -> 聚合启动前后端

echo 🚀 Starting ScholarFlow...

:: 1. 清理旧进程 (防止端口冲突)
echo 🧹 Cleaning up old processes...
taskkill /F /IM uvicorn.exe /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq ScholarFlow*" /T >nul 2>&1

:: 2. 加载环境变量 (优先根目录 .env，其次 backend\.env)
if exist .env (
  echo 📄 Loading root environment variables...
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)
if exist backend\.env (
  echo 📄 Loading backend environment variables...
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("backend\.env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

:: 3. 启动后端 (后台模式运行在当前窗口)
echo 🐍 Starting Backend (FastAPI on :8000)...
set "BACKEND_RELOAD=%BACKEND_RELOAD%"
if "%BACKEND_RELOAD%"=="" set "BACKEND_RELOAD=1"

cd backend
if "%BACKEND_RELOAD%"=="1" (
    start /B uvicorn main:app --host 0.0.0.0 --port 8000 --reload
) else (
    start /B uvicorn main:app --host 0.0.0.0 --port 8000
)
cd ..

:: 4. 启动前端 (前台模式，聚合日志)
echo ⚛️  Starting Frontend (Next.js on :3000)...
set "NODE_OPTIONS=--dns-result-order=ipv4first"
set "FORCE_COLOR=1"
cd frontend
echo ✅ ScholarFlow is running!
echo 👉 Frontend: http://localhost:3000
echo 👉 Backend:  http://localhost:8000/docs
echo Press Ctrl+C to stop.
echo ---------------------------------------------------
pnpm dev

:: 结束后尝试清理后端
taskkill /F /IM uvicorn.exe /T >nul 2>&1