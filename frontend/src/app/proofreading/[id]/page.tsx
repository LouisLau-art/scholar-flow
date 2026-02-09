'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { ManuscriptApi } from '@/services/manuscriptApi'
import { ProofreadingForm } from '@/components/author/proofreading/ProofreadingForm'
import type { ProofreadingContext } from '@/types/production'

export default function ProofreadingPage() {
  const params = useParams()
  const manuscriptId = String((params as Record<string, string>)?.id || '')

  const [loading, setLoading] = useState(true)
  const [context, setContext] = useState<ProofreadingContext | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await ManuscriptApi.getProofreadingContext(manuscriptId)
      if (!res?.success || !res?.data) {
        throw new Error(res?.detail || res?.message || 'Failed to load proofreading context')
      }
      const next = res.data as ProofreadingContext
      setContext(next)

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
      <main className="flex min-h-screen items-center justify-center bg-slate-100">
        <Loader2 className="h-6 w-6 animate-spin text-slate-600" />
      </main>
    )
  }

  if (!context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6 text-sm text-slate-600">
        No active proofreading task for this manuscript.
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Author Proofreading</p>
            <h1 className="truncate text-lg font-semibold text-slate-900 sm:text-xl">{context.manuscript.title || 'Untitled Manuscript'}</h1>
            <p className="text-xs text-slate-500">Cycle #{context.cycle.cycle_no} · Status: {status}</p>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回 Dashboard
          </Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-4 px-4 py-4 md:grid-cols-12 sm:px-6">
        <section className="md:col-span-7">
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            {pdfUrl ? (
              <iframe title="Proofreading Galley" src={pdfUrl} className="h-[calc(100vh-140px)] min-h-[560px] w-full" />
            ) : (
              <div className="flex h-[calc(100vh-140px)] min-h-[560px] items-center justify-center text-sm text-slate-500">
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
