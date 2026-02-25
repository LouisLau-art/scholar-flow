'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { authService } from '@/services/auth'
import { Loader2, FileText, ArrowLeft, Download, Clock3, Shield } from 'lucide-react'
import Link from 'next/link'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type TimelineAttachment =
  | { type: 'review_attachment'; label: string; download_url: string }
  | { type: 'manuscript_pdf'; label: string; download_url: string }
  | { type: 'decision_attachment'; label: string; signed_url_api: string }

type TimelineEvent = {
  id: string
  timestamp: string
  actor: 'author' | 'editorial' | 'reviewer' | 'system'
  title: string
  message: string
  attachments?: TimelineAttachment[]
}

type AuthorContextPayload = {
  manuscript: {
    id: string
    title: string
    status: string
    status_label: string
    created_at: string | null
    updated_at: string | null
  }
  files: {
    current_pdf_signed_url: string | null
    cover_letters: Array<{
      id: string
      filename: string
      content_type?: string | null
      created_at: string | null
      signed_url: string | null
    }>
  }
  proofreading_task?: {
    cycle_id?: string
    cycle_no?: number
    status?: string
    proof_due_at?: string | null
    action_required?: boolean
    url?: string
  } | null
  timeline: TimelineEvent[]
}

export default function AuthorManuscriptReviewsPage({ params }: { params: { id: string } }) {
  const [isLoading, setIsLoading] = useState(true)
  const [ctx, setCtx] = useState<AuthorContextPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const token = await authService.getAccessToken()
        if (!token) {
          setError('Please sign in again.')
          return
        }
        const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(params.id)}/author-context`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const json = await res.json().catch(() => null)
        if (!res.ok || !json?.success) {
          setError(json?.detail || json?.message || 'Failed to load review feedback.')
          return
        }
        setCtx((json.data || null) as AuthorContextPayload)
      } catch (e) {
        setError('Failed to load manuscript timeline.')
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [params.id])

  const openSignedUrl = async (apiUrl: string) => {
    try {
      const token = await authService.getAccessToken()
      if (!token) return
      const res = await fetch(apiUrl, { headers: { Authorization: `Bearer ${token}` } })
      const json = await res.json().catch(() => null)
      const signedUrl = json?.data?.signed_url || json?.data?.signedUrl || json?.data?.signedURL
      if (res.ok && signedUrl) {
        window.open(String(signedUrl), '_blank')
      }
    } catch (e) {
      // ignore
    }
  }

  const actorLabel = (actor: TimelineEvent['actor']) => {
    if (actor === 'author') return { text: 'Author', icon: null }
    if (actor === 'reviewer') return { text: 'Reviewer', icon: <Shield className="h-3.5 w-3.5" /> }
    if (actor === 'editorial') return { text: 'Editorial Office', icon: <Shield className="h-3.5 w-3.5" /> }
    return { text: 'System', icon: null }
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-5xl w-full px-4 py-10">
        <div className="mb-6">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>

        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-serif font-bold text-foreground">{ctx?.manuscript?.title || 'Manuscript'}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Reviewer identities and confidential notes are hidden. Only author-visible feedback is shown here.
            </p>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="mt-8 rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-sm text-destructive">
              {error}
            </div>
          ) : !ctx ? (
            <div className="mt-8 rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
              No data available.
            </div>
          ) : (
            <div className="space-y-8">
              <Card className="shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Current Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{ctx.manuscript.status_label || ctx.manuscript.status}</Badge>
                    {ctx.manuscript.updated_at ? (
                      <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock3 className="h-3.5 w-3.5" />
                        Updated {new Date(ctx.manuscript.updated_at).toLocaleString()}
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {ctx.proofreading_task?.action_required ? (
                      <Link
                        href={ctx.proofreading_task.url || `/proofreading/${ctx.manuscript.id}`}
                        className={cn(buttonVariants({ variant: 'default', size: 'sm' }))}
                      >
                        开始校对 Proof
                      </Link>
                    ) : null}
                    {ctx.files.current_pdf_signed_url ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(String(ctx.files.current_pdf_signed_url), '_blank')}
                      >
                        <FileText className="h-4 w-4 mr-2" />
                        Download Manuscript PDF
                      </Button>
                    ) : null}
                    {ctx.files.cover_letters?.length ? (
                      ctx.files.cover_letters.map((f) => (
                        <Button
                          key={f.id}
                          variant="outline"
                          size="sm"
                          disabled={!f.signed_url}
                          onClick={() => f.signed_url && window.open(String(f.signed_url), '_blank')}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Cover Letter: {f.filename}
                        </Button>
                      ))
                    ) : null}
                  </div>
                </CardContent>
              </Card>

              <section className="space-y-4">
                <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Activity Timeline</h2>
                {ctx.timeline?.length ? (
                  <div className="space-y-4">
                    {ctx.timeline.map((ev) => {
                      const a = actorLabel(ev.actor)
                      return (
                        <Card key={ev.id} className="shadow-sm border-border">
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between gap-4">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="inline-flex items-center gap-1">
                                    {a.icon}
                                    {a.text}
                                  </Badge>
                                  <div className="text-sm font-semibold text-foreground">{ev.title}</div>
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '—'}
                                </div>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {ev.message ? (
                              ev.actor === 'author' ? (
                                <div
                                  className="prose prose-sm max-w-none rounded-md border border-border bg-muted/50 p-3"
                                  // 注意：response_letter 允许内嵌图片(Data URL)，用于对账与可追溯；MVP 不做后端清洗。
                                  dangerouslySetInnerHTML={{ __html: String(ev.message) }}
                                />
                              ) : (
                                <div className="whitespace-pre-wrap rounded-md border border-border bg-muted/50 p-3 text-sm text-foreground">
                                  {ev.message}
                                </div>
                              )
                            ) : null}

                            {Array.isArray(ev.attachments) && ev.attachments.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {ev.attachments.map((att, idx) => {
                                  if (att.type === 'review_attachment') {
                                    return (
                                      <Button
                                        key={`${ev.id}-att-${idx}`}
                                        size="sm"
                                        variant="outline"
                                        onClick={() => window.open(att.download_url, '_blank')}
                                      >
                                        <Download className="h-4 w-4 mr-2" />
                                        {att.label}
                                      </Button>
                                    )
                                  }
                                  if (att.type === 'manuscript_pdf') {
                                    return (
                                      <Button
                                        key={`${ev.id}-att-${idx}`}
                                        size="sm"
                                        variant="outline"
                                        onClick={() => void openSignedUrl(att.download_url)}
                                      >
                                        <FileText className="h-4 w-4 mr-2" />
                                        {att.label}
                                      </Button>
                                    )
                                  }
                                  if (att.type === 'decision_attachment') {
                                    return (
                                      <Button
                                        key={`${ev.id}-att-${idx}`}
                                        size="sm"
                                        variant="outline"
                                        onClick={() => void openSignedUrl(att.signed_url_api)}
                                      >
                                        <Download className="h-4 w-4 mr-2" />
                                        {att.label}
                                      </Button>
                                    )
                                  }
                                  return null
                                })}
                              </div>
                            ) : null}
                          </CardContent>
                        </Card>
                      )
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">
                    No activity yet.
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
