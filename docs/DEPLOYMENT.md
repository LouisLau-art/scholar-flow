# 部署指南（Vercel + Render，云端 Supabase）

本项目默认使用**云端 Supabase**（`mmvulyrfsorqdpdrzbkd`）作为数据库/鉴权/存储。

## 0) 部署前检查清单（必做）

1. **云端迁移已同步**
   - 推荐：在 repo root 执行 `supabase db push --linked`
   - 若 CLI 不可用：把 `supabase/migrations/*.sql` 依次粘贴到 Supabase Dashboard → SQL Editor 执行

2. **Supabase Auth 回调配置**
   - Dashboard → Authentication → URL Configuration
   - 把 Vercel 域名加入：
     - `Site URL`: `https://<你的vercel域名>`
     - `Redirect URLs`: `https://<你的vercel域名>/auth/callback`

3. **后端生产环境必须关闭 dev-login**
   - Render 上设置：`GO_ENV=prod`（或任何非 `dev` 值）

---

## 1) 后端部署到 Render（FastAPI）

### A. Render 服务配置（推荐）

- **Root Directory**: `backend`（这是一个前后端同仓库的 monorepo）
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### B. Render 环境变量（必填）

- `SUPABASE_URL`：你的 Supabase Project URL
- `SUPABASE_SERVICE_ROLE_KEY`：Supabase `service_role` key（只放后端）
- `FRONTEND_ORIGIN`：你的 Vercel 域名，例如 `https://xxx.vercel.app`
- `GO_ENV`：`prod`

### C. Render 环境变量（可选 / 推荐）

- `PLAGIARISM_CHECK_ENABLED=0`（MVP 默认关闭查重）
- `PRODUCTION_GATE_ENABLED=0`（MVP 默认只做 Payment Gate；若要强制 production final PDF 才能发布，设为 `1` 并确保云端已执行 `supabase/migrations/20260203143000_post_acceptance_pipeline.sql`）
- `MATCHMAKING_WARMUP=1`（可选：后端启动后异步预热 embedding 模型，避免 editor 第一次点“AI 推荐”卡顿）

> 说明：如果 Render 没有挂载持久化磁盘，HuggingFace 模型缓存可能在每次重新部署后需要重新下载；这是平台行为，不是代码 bug。

---

## 2) 前端部署到 Vercel（Next.js 14 App Router）

### A. Vercel 项目 Root Directory

这是一个 monorepo，Vercel 创建项目时把 **Root Directory 设置为 `frontend`**（否则可能无法识别 Next.js 项目）。

### B. 关键点：`/api/v1/*` 通过 rewrites 代理到后端

本项目大量前端请求使用相对路径 `/api/v1/...`，依赖 `frontend/next.config.mjs` 的 rewrites。
因此 **Vercel 必须设置 `BACKEND_ORIGIN`**（否则会默认指向本地 `127.0.0.1:8000` 而失败）。

### C. Vercel 环境变量（必填）

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `BACKEND_ORIGIN`：你的 Render 后端基址，例如 `https://scholarflow-backend.onrender.com`

### D. Vercel 环境变量（可选）

- `APP_ENV=production` / `staging`（若你启用了 staging banner 逻辑）

---

## 3) 生产连通性自检（上线后 3 分钟内完成）

1. 打开前端首页，确认网络请求的 `/api/v1/cms/menu` / `/api/v1/manuscripts/published/latest` 有响应
2. 登录后打开 `/dashboard`，确认 `/api/v1/user/profile` 返回 200
3. 打开一篇 `published` 文章页 `/articles/<id>`，确认 PDF 预览不会请求 Supabase `storage/v1/object/sign`（应改为调用后端 `/api/v1/manuscripts/articles/<id>/pdf-signed`）
