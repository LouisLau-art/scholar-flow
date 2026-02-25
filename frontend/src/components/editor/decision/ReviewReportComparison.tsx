'use client'

import type { DecisionReport } from '@/types/decision'

type ReviewReportComparisonProps = {
  reports: DecisionReport[]
}

function formatScore(score: number | null | undefined): string {
  if (score == null) return 'N/A'
  return String(score)
}

export function ReviewReportComparison({ reports }: ReviewReportComparisonProps) {
  if (!reports.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
        No submitted reports yet.
      </div>
    )
  }

  const isDual = reports.length <= 2
  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Review Reports</h2>
        <p className="mt-1 text-xs text-muted-foreground">Only submitted reports are shown here.</p>
      </div>

      <div className={isDual ? 'grid grid-cols-1 gap-3 xl:grid-cols-2' : 'space-y-3'}>
        {reports.map((report, index) => (
          <article key={report.id} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Reviewer {index + 1}: {report.reviewer_name || report.reviewer_email || 'Unknown'}
                </h3>
                <p className="text-xs text-muted-foreground">Score: {formatScore(report.score)}</p>
              </div>
              <span className="rounded-full bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground">
                {report.status || 'submitted'}
              </span>
            </div>

            <div className="mt-3 rounded-md border border-border bg-muted/50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Comments for author</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">
                {report.comments_for_author || '(No comment provided)'}
              </p>
            </div>

            <details className="mt-3 rounded-md border border-border bg-card p-3">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Confidential comments to editor
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                {report.confidential_comments_to_editor || '(None)'}
              </p>
            </details>

            {report.attachment?.signed_url ? (
              <a
                href={report.attachment.signed_url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex text-xs font-semibold text-primary hover:underline"
              >
                下载审稿附件
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  )
}
