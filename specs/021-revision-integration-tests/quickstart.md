# Quickstart: Running Integration Tests

## 1. Prerequisites

确保 Supabase 连接可用（默认使用云端 Supabase；如果你在本地跑 Supabase，则先启动；使用云端可跳过这一步）：
```bash
supabase start
```

## 2. Backend Integration Tests

Run the revision cycle test suite:
```bash
cd backend
pytest -o addopts= tests/integration/test_revision_cycle.py -v
```

说明：`backend/pytest.ini` 默认开启了覆盖率门槛（`--cov-fail-under=80`），所以“只跑这个文件”时建议用 `-o addopts=` 避免被全局门槛卡住。

**Common Flags:**
- `-s`: Show stdout (for debugging prints).
- `-x`: Stop on first failure.

## 3. Frontend E2E Tests

Run the revision flow Playwright spec:
```bash
cd frontend
npx playwright test tests/e2e/specs/revision_flow.spec.ts --project=chromium
```

**Headless vs UI Mode:**
- Default is headless.
- To watch execution: `npx playwright test tests/e2e/specs/revision_flow.spec.ts --ui`

**端口/起服务说明：**
- Playwright 会自动启动 Next dev server（可复用已存在的 server）。
- 默认端口是 `3000`。如果端口被占用或你想换端口：
  - `PLAYWRIGHT_PORT=3001 npx playwright test tests/e2e/specs/revision_flow.spec.ts --project=chromium`
- 如果你想完全禁用 Playwright 自动起服务（前提是你已经手动 `npm run dev` 并保持运行）：
  - `PLAYWRIGHT_WEB_SERVER=0 npx playwright test tests/e2e/specs/revision_flow.spec.ts --project=chromium`

**CI-like 跑法（推荐）：**
- Backend：`cd backend && CI=1 pytest -o addopts= tests/integration/test_revision_cycle.py -v`
- Frontend：`cd frontend && CI=1 npx playwright test tests/e2e/specs/revision_flow.spec.ts --project=chromium`

## 4. Troubleshooting

- **Auth Errors**: Ensure `SUPABASE_SERVICE_ROLE_KEY` is set in `.env` for backend tests.
- **Database State**: If tests fail due to existing data, restart Supabase (`supabase stop && supabase start`) to reset.
