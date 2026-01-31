import type { FullConfig } from '@playwright/test'

import { callInternalTestApi } from './utils'

export default async function globalSetup(_config: FullConfig) {
  // 中文注释:
  // - Feature 016 要求：E2E 运行前必须 reset + seed，保证“干净状态”。
  // - 但本仓库也支持仅跑“前端路由 mock”的轻量用例，因此这里做“可选启用”。
  // - 开启条件：E2E_ENABLE_DB_RESET=true 且配置了 E2E_ADMIN_BEARER_TOKEN。
  if ((process.env.E2E_ENABLE_DB_RESET || '').toLowerCase() !== 'true') return

  await callInternalTestApi('/reset-db')
  await callInternalTestApi('/seed-db')
}

