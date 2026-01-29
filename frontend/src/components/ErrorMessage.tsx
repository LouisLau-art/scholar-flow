type ErrorMessageProps = {
  message: string
  tone?: 'error' | 'warning' | 'info'
}

const toneClasses: Record<NonNullable<ErrorMessageProps['tone']>, string> = {
  error: 'border-red-200 bg-red-50 text-red-700',
  warning: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  info: 'border-blue-200 bg-blue-50 text-blue-700',
}

export default function ErrorMessage({ message, tone = 'error' }: ErrorMessageProps) {
  return (
    <div
      className={`rounded-md border px-3 py-2 text-sm ${toneClasses[tone]}`}
      data-testid="error-message"
    >
      {message}
    </div>
  )
}
