const FALLBACK_NOTIFICATION_URL = '/dashboard/notifications'

export function resolveNotificationUrl(actionUrl?: string | null, fallback: string = FALLBACK_NOTIFICATION_URL): string {
  const raw = String(actionUrl || '').trim()
  if (!raw) return fallback

  if (raw.startsWith('/')) return raw
  if (raw.startsWith('./')) return `/${raw.slice(2)}`

  try {
    const parsed = new URL(raw)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return fallback
    }
    const path = parsed.pathname || '/'
    if (!path.startsWith('/')) return fallback
    return `${path}${parsed.search || ''}${parsed.hash || ''}`
  } catch {
    return fallback
  }
}

