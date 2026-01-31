'use client'

type LoginPromptProps = {
  message?: string
  actionHref?: string
  actionLabel?: string
}

export default function LoginPrompt({
  message = 'Please log in to submit a manuscript.',
  actionHref = '/login',
  actionLabel = 'Login here',
}: LoginPromptProps) {
  return (
    <div
      className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-yellow-800 text-sm"
      data-testid="submission-login-prompt"
    >
      ⚠️ {message}
      <a href={actionHref} className="ml-1 font-semibold underline">
        {actionLabel}
      </a>
    </div>
  )
}
