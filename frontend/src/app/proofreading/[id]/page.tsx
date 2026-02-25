'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { ManuscriptApi } from '@/services/manuscriptApi'
import { ProofreadingForm } from '@/components/author/proofreading/ProofreadingForm'
import type { ProofreadingContext } from '@/types/production'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function ProofreadingPage() {
  const params = useParams()
  const manuscriptId = String((params as Record<string, string>)?.id || '')

  const [loading, setLoading] = useState(true)
  const [context, setContext] = useState<ProofreadingContext | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [noTaskMessage, setNoTaskMessage] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await ManuscriptApi.getProofreadingContext(manuscriptId)
      if (!res?.success || !res?.data) {
        const msg = String(res?.detail || res?.message || '').trim()
        const lowered = msg.toLowerCase()
        if (
          lowered.includes('no proofreading task') ||
          lowered.includes('no active proofreading task') ||
          lowered.includes('not found')
        ) {
          // 中文注释: 作者可能已提交校对反馈或该稿件尚未进入校对阶段，此时不应作为“报错”处理。
          setContext(null)
          setPdfUrl(null)
          setNoTaskMessage(msg || '当前没有可操作的校对任务。')
          return
        }
        throw new Error(msg || 'Failed to load proofreading context')
      }
      const next = res.data as ProofreadingContext
      setContext(next)
      setNoTaskMessage(null)

      if (next.cycle?.galley_signed_url) {
        setPdfUrl(next.cycle.galley_signed_url)
      } else {
        const signedRes = await ManuscriptApi.getProductionGalleySignedUrl(manuscriptId, next.cycle.id)
        if (signedRes?.success && signedRes?.data?.signed_url) {
          setPdfUrl(String(signedRes.data.signed_url))
        } else {
          setPdfUrl(null)
        }
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load proofreading context')
      setContext(null)
      setPdfUrl(null)
      setNoTaskMessage(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!manuscriptId) return
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  const status = useMemo(() => context?.cycle?.status || '--', [context])

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </main>
    )
  }

  if (!context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40 px-6">
        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle className="text-base">作者校对</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>{noTaskMessage || '当前没有可操作的校对任务。'}</p>
            <p className="text-xs text-muted-foreground">
              如果你刚提交完校对反馈：说明本轮校对已结束或已进入编辑处理阶段，请返回 Dashboard 查看最新状态。
            </p>
            <Link href="/dashboard" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
              <ArrowLeft className="h-4 w-4" />
              返回 Dashboard
            </Link>
          </CardContent>
        </Card>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-muted/40">
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex sf-max-w-1600 items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Author Proofreading</p>
            <h1 className="truncate text-lg font-semibold text-foreground sm:text-xl">{context.manuscript.title || 'Untitled Manuscript'}</h1>
            <p className="text-xs text-muted-foreground">Cycle #{context.cycle.cycle_no} · Status: {status}</p>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            返回 Dashboard
          </Link>
        </div>
      </header>

      <div className="mx-auto grid sf-max-w-1600 grid-cols-1 gap-4 px-4 py-4 md:grid-cols-12 sm:px-6">
        <section className="md:col-span-7">
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            {pdfUrl ? (
              <iframe title="Proofreading Galley" src={pdfUrl} className="h-[calc(100vh-140px)] min-h-[560px] w-full" />
            ) : (
              <div className="flex h-[calc(100vh-140px)] min-h-[560px] items-center justify-center text-sm text-muted-foreground">
                Galley preview is unavailable.
              </div>
            )}
          </div>
        </section>

        <section className="md:col-span-5">
          <ProofreadingForm manuscriptId={manuscriptId} context={context} onSubmitted={load} />
        </section>
      </div>
    </main>
  )
}
