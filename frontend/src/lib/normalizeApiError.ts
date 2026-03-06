export function normalizeApiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback

  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string' && detail.trim()) return detail

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown; loc?: unknown }
    const msg = typeof first?.msg === 'string' ? first.msg.trim() : ''
    const loc = Array.isArray(first?.loc) ? first.loc.map((item) => String(item)).join('.') : ''
    if (msg && loc) return `${msg} (${loc})`
    if (msg) return msg
  }

  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) return message
    try {
      return JSON.stringify(detail)
    } catch {
      return fallback
    }
  }

  const message = (payload as { message?: unknown }).message
  if (typeof message === 'string' && message.trim()) return message

  return fallback
}
