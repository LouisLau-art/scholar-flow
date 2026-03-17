# ScholarFlow AI / Agent Operator Context Pack

更新时间：2026-03-17  
预期读者：未来继续接手 ScholarFlow 的 AI agent 或技术同事  
文档目标：提供可直接喂给大模型的、低歧义的、面向执行的上下文

## 1. Mission

你的任务不是重构 ScholarFlow，也不是重新设计平台架构。

你的任务是：

- 在不依赖原负责人个人账号的前提下继续让系统可运行
- 发现故障时先修平台联通与配置，而不是先改业务逻辑
- 只在必要时推进后续平台去个人化工作

## 2. Current Verified Facts

以下事实在 2026-03-17 已现场验证：

- Frontend URL: `https://scholar-flow-7msj.vercel.app`
- Backend URL: `https://louis-liu-yujian-scholarflow-api.hf.space`
- `GET frontend /api/v1/cms/menu?location=header` returns 200
- `GET backend /api/v1/public/journals` returns 200
- Hugging Face backend has already moved from personal namespace to `louis-liu-yujian` organization
- Supabase remains the current cloud project `mmvulyrfsorqdpdrzbkd`
- Successor already has access to Supabase and Resend
- Sentry is not yet fully handed over, but it is not a blocker for keeping the system running

## 3. Current Platform State

| Platform | Current State | Operational Meaning |
| --- | --- | --- |
| Supabase | Existing cloud project still in use | Do not assume DB migration already happened |
| Hugging Face Space | Already moved to org namespace | Old personal Space URL is obsolete |
| Vercel | Successor-controlled frontend deployment is working | Frontend traffic should target new HF backend |
| Resend | Successor is already in the current team | Email platform is minimally handed over |
| Sentry | Pending | Optional for now |

## 4. Stop Assuming These Things

- Do not assume old HF URL `louisshawn-scholarflow-api.hf.space` is still valid
- Do not assume changing env vars without redeploy is enough
- Do not assume Sentry is required before system can run
- Do not assume the project already moved to a new company-owned Supabase project
- Do not assume repository templates always reflect live platform values

## 5. Source of Truth Priority

When facts conflict, trust sources in this order:

1. Live platform behavior
2. Current platform dashboard values
3. Current runtime probes
4. Repository handoff docs
5. Historical templates and old deployment notes

## 6. Primary Operational URLs

- Frontend: `https://scholar-flow-7msj.vercel.app`
- Backend root: `https://louis-liu-yujian-scholarflow-api.hf.space`
- Backend journals probe: `https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/public/journals`
- Frontend rewrite probe: `https://scholar-flow-7msj.vercel.app/api/v1/cms/menu?location=header`
- Backend runtime version: `https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/internal/runtime-version`
- Resend webhook endpoint: `https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/internal/webhooks/resend`

## 7. Minimal Environment Matrix

## 7.1 Vercel

Required:

- `NEXT_PUBLIC_API_URL=https://louis-liu-yujian-scholarflow-api.hf.space`
- `NEXT_PUBLIC_SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=[dashboard value]`

Recommended:

- `BACKEND_ORIGIN=https://louis-liu-yujian-scholarflow-api.hf.space`

Notes:

- `BACKEND_ORIGIN` is recommended because rewrites read it first
- A redeploy is required after env changes

## 7.2 HF Space

Core:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `FRONTEND_ORIGIN`
- `ADMIN_API_KEY`
- `MAGIC_LINK_JWT_SECRET`

Mail:

- `RESEND_API_KEY`
- `EMAIL_SENDER`
- `RESEND_WEBHOOK_SECRET`

## 7.3 Supabase

Current role of the platform:

- Database
- Auth
- Storage

Current policy:

- Continue using the existing cloud project
- Do not start database migration unless explicitly asked

## 8. Most Likely Failure Patterns

## 8.1 Frontend loads but Dashboard/API data fails

Most likely causes:

- Wrong `NEXT_PUBLIC_API_URL`
- Wrong `BACKEND_ORIGIN`
- Env vars changed but Vercel was not redeployed
- Vercel scope mismatch between Preview and Production

Fast check:

- If frontend `/api/v1/*` returns Vercel HTML 404, rewrite is broken
- If backend direct URL returns JSON 200/401, backend is alive

## 8.2 Backend moved, frontend still points to old Space

Most likely causes:

- HF Space namespace changed but Vercel envs were not updated
- Old URLs survived in templates or old notes

Fast check:

- Compare current HF Space URL with current Vercel envs

## 8.3 Email sending fails

Most likely causes:

- Missing `RESEND_API_KEY`
- Invalid `EMAIL_SENDER`
- Still using fallback sender on `resend.dev`
- Missing `RESEND_WEBHOOK_SECRET`

## 9. High-Value Probes

```bash
curl -fsS https://scholar-flow-7msj.vercel.app/api/v1/cms/menu?location=header
```

```bash
curl -fsS https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/public/journals
```

```bash
curl -H "X-Admin-Key: <ADMIN_API_KEY>" \
  https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/internal/runtime-version
```

## 10. Local Fallback Mode

If cloud routing is unstable, run locally before attempting bigger migrations.

### Frontend local env

```ini
NEXT_PUBLIC_SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[dashboard value]
BACKEND_ORIGIN=http://127.0.0.1:8000
```

### Backend local env

```ini
SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co
SUPABASE_ANON_KEY=[dashboard value]
SUPABASE_SERVICE_ROLE_KEY=[dashboard value]
FRONTEND_ORIGIN=http://localhost:3000
GO_ENV=dev
```

### Start command

```bash
./start.sh
```

## 11. Explicit Non-Goals

Do not prioritize these unless the user explicitly asks:

- Sentry migration
- Supabase full re-hosting
- Platform naming cleanup
- Documentation beautification
- Non-runtime refactors

## 12. Operational Rule of Thumb

When something breaks after a platform change:

- first check URLs
- then check env scope
- then redeploy/restart
- only then consider code changes

## 13. Most Relevant Repo Files

- `frontend/next.config.mjs`
- `frontend/src/lib/backend-origin.ts`
- `frontend/src/components/submission/submission-form-utils.ts`
- `backend/app/api/v1/internal.py`
- `backend/app/core/mail.py`
- `scripts/platform-env.example`
- `scripts/sync-platform-env.sh`
- `scripts/ci/check-platform-readiness.sh`
- `docs/handoff/2026-03-17-technical-successor-cutover-runbook.md`

## 14. One-Sentence Summary

ScholarFlow is currently in a workable transitional state: Supabase, HF Space, Vercel, and Resend are sufficiently handed over for continued operation, while Sentry remains optional and old platform URLs/templates must not be trusted blindly.
