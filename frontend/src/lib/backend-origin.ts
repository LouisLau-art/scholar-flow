const LOCAL_DEV_BACKEND_ORIGIN = 'http://127.0.0.1:8000'

function normalizeBackendOrigin(raw?: string | null): string | null {
  const value = String(raw || '').trim()
  return value ? value.replace(/\/$/, '') : null
}

export function getConfiguredBackendOrigin(): string | null {
  return normalizeBackendOrigin(
    process.env.BACKEND_ORIGIN || process.env.NEXT_PUBLIC_API_URL
  )
}

export function getServerBackendOrigin(): string | null {
  const configured = getConfiguredBackendOrigin()
  if (configured) return configured

  // 中文注释：
  // - 开发环境允许默认回落到本地 FastAPI，保持 `./start.sh` 的零配置体验。
  // - 生产构建阶段若未显式配置后端地址，则直接放弃请求，由页面自己走 fallback，
  //   避免 `next build` 卡在 127.0.0.1 的长时间超时。
  if (process.env.NODE_ENV !== 'production') {
    return LOCAL_DEV_BACKEND_ORIGIN
  }

  return null
}

export function getBackendOrigin(): string {
  return getServerBackendOrigin() || LOCAL_DEV_BACKEND_ORIGIN
}
