import { getServerBackendOrigin } from '@/lib/backend-origin'

type BackendFetchNextOptions = {
  revalidate?: number | false
  tags?: string[]
}

type BackendJsonFetchOptions = Omit<RequestInit, 'signal'> & {
  next?: BackendFetchNextOptions
  timeoutMs?: number
  label?: string
}

type BackendJsonFetchResult<T> = {
  ok: boolean
  status: number
  data: T | null
}

const DEFAULT_SERVER_BACKEND_TIMEOUT_MS = 4000

export async function fetchBackendJson<T>(
  path: string,
  options: BackendJsonFetchOptions = {}
): Promise<BackendJsonFetchResult<T>> {
  const origin = getServerBackendOrigin()
  if (!origin) {
    return {
      ok: false,
      status: 0,
      data: null,
    }
  }

  const {
    timeoutMs = DEFAULT_SERVER_BACKEND_TIMEOUT_MS,
    label = path,
    ...fetchInit
  } = options

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${origin}${path}`, {
      ...fetchInit,
      signal: controller.signal,
    })
    const payload = (await response.json().catch(() => null)) as T | null
    return {
      ok: response.ok,
      status: response.status,
      data: payload,
    }
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(`[server-backend-fetch] ${label} failed`, error)
    }
    return {
      ok: false,
      status: 0,
      data: null,
    }
  } finally {
    clearTimeout(timeout)
  }
}
