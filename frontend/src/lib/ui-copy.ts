export const UI_COPY = {
  loading: 'Loading…',
  submitting: 'Submitting…',
  confirming: 'Confirming…',
  removing: 'Removing…',
} as const

export function withEllipsis(base: string): string {
  return `${base.trim().replace(/\.+$/, '')}…`
}
