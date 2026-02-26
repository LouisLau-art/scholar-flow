function toValidDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatLocal(
  value: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions
): string {
  const date = toValidDate(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat(undefined, options).format(date)
}

export function formatDateLocal(value: string | Date | null | undefined): string {
  return formatLocal(value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

export function formatDateTimeLocal(value: string | Date | null | undefined): string {
  return formatLocal(value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatDateTimeWithSecondsLocal(value: string | Date | null | undefined): string {
  return formatLocal(value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}
