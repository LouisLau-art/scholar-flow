export default function ReviewLinkErrorPage({
  searchParams,
}: {
  searchParams?: { reason?: string }
}) {
  const reason = (searchParams?.reason || '').toLowerCase()
  const message =
    reason === 'expired'
      ? 'This invitation link has expired.'
      : 'This invitation link is invalid or has been revoked.'

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Unable to Open Invitation</h1>
        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
        <div className="mt-4 rounded-md bg-muted/50 p-4 text-sm text-foreground">
          Please contact the editorial office and request a new invitation link.
        </div>
      </div>
    </div>
  )
}
