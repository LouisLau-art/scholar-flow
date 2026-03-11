function toValidDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

const DATE_DISPLAY_LOCALE = 'zh-CN'
const DATE_DISPLAY_TIME_ZONE = 'Asia/Shanghai'

function toDateParts(value: string | Date | null | undefined) {
  const date = toValidDate(value)
  if (!date) return null

  const parts = new Intl.DateTimeFormat(DATE_DISPLAY_LOCALE, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: DATE_DISPLAY_TIME_ZONE,
  }).formatToParts(date)

  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''

  return {
    year: get('year'),
    month: get('month'),
    day: get('day'),
    hour: get('hour'),
    minute: get('minute'),
    second: get('second'),
  }
}

export function formatDateLocal(value: string | Date | null | undefined): string {
  const parts = toDateParts(value)
  if (!parts) return '—'
  return `${parts.year}/${parts.month}/${parts.day}`
}

export function formatDateTimeLocal(value: string | Date | null | undefined): string {
  const parts = toDateParts(value)
  if (!parts) return '—'
  return `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`
}

export function formatDateTimeWithSecondsLocal(value: string | Date | null | undefined): string {
  const parts = toDateParts(value)
  if (!parts) return '—'
  return `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`
}
