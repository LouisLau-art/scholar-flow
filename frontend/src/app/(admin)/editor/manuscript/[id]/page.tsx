'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'
import { EditorApi } from '@/services/editorApi'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { getStatusBadgeClass, getStatusLabel } from '@/lib/statusStyles'
import { toast } from 'sonner'
import { ArrowLeft, Loader2, FileText, Pencil } from 'lucide-react'

type ManuscriptDetail = any

function allowedNext(status: string): string[] {
  const s = (status || '').toLowerCase()
  if (s === 'pre_check') return ['under_review', 'minor_revision', 'rejected']
  if (s === 'under_review') return ['decision', 'major_revision', 'minor_revision', 'rejected']
  if (s === 'major_revision' || s === 'minor_revision') return ['resubmitted']
  if (s === 'resubmitted') return ['under_review', 'decision', 'major_revision', 'minor_revision', 'rejected']
  if (s === 'decision') return ['decision_done']
  if (s === 'decision_done') return ['approved', 'rejected']
  if (s === 'approved') return ['layout']
  if (s === 'layout') return ['english_editing', 'proofreading']
  if (s === 'english_editing') return ['proofreading']
  if (s === 'proofreading') return ['published']
  return []
}

export default function EditorManuscriptDetailPage() {
  const params = useParams()
  const id = String((params as any).id || '')

  const [loading, setLoading] = useState(true)
  const [ms, setMs] = useState<ManuscriptDetail | null>(null)
  const [pdfSignedUrl, setPdfSignedUrl] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState<string | null>(null)

  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [invAuthors, setInvAuthors] = useState('')
  const [invAffiliation, setInvAffiliation] = useState('')
  const [invApc, setInvApc] = useState('')
  const [invFunding, setInvFunding] = useState('')
  const [invoiceSaving, setInvoiceSaving] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const detailRes = await EditorApi.getManuscriptDetail(id)
      if (!detailRes?.success) throw new Error(detailRes?.detail || detailRes?.message || 'Manuscript not found')
      const detail = detailRes.data
      setMs(detail)

      const pdf = await fetch(`/api/v1/manuscripts/${id}/pdf-signed`).then((r) => r.json())
      if (pdf?.success) setPdfSignedUrl(pdf.data?.signed_url || null)
      else setPdfSignedUrl(null)

      const meta = (detail?.invoice_metadata as any) || {}
      setInvAuthors(String(meta.authors || ''))
      setInvAffiliation(String(meta.affiliation || ''))
      setInvApc(meta.apc_amount != null ? String(meta.apc_amount) : '')
      setInvFunding(String(meta.funding_info || ''))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load manuscript')
      setMs(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const status = String(ms?.status || '')
  const nextStatuses = useMemo(() => allowedNext(status), [status])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 flex items-center justify-center text-slate-500 gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading…
        </div>
      </div>
    )
  }

  if (!ms) {
    return (
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 text-slate-600">Manuscript not found.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-serif font-bold text-slate-900 tracking-tight">
                Manuscript Details
              </h1>
              <p className="mt-1 font-mono text-xs text-slate-400">{id}</p>
            </div>
          </div>
          <Link href="/dashboard?tab=editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-8 space-y-6">
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-lg">PDF Preview</CardTitle>
                  <p className="text-sm text-slate-500">通过 signed URL 预览（避免 Storage RLS 影响）</p>
                </div>
              </CardHeader>
              <CardContent>
                {pdfSignedUrl ? (
                  <div className="rounded-xl border border-slate-200 overflow-hidden bg-white">
                    <iframe
                      title="Manuscript PDF"
                      src={pdfSignedUrl}
                      className="w-full h-[calc(100vh-260px)] min-h-[720px]"
                    />
                  </div>
                ) : (
                  <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
                    PDF not available.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-4 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Status</span>
                  <Badge className={`border ${getStatusBadgeClass(status)}`}>{getStatusLabel(status)}</Badge>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Owner</span>
                  <span className="text-slate-900 text-right">
                    {ms.owner?.full_name || ms.owner?.email || '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Assign Editor</span>
                  <span className="text-slate-900 text-right">
                    {ms.editor?.full_name || ms.editor?.email || '—'}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-lg">Invoice Info</CardTitle>
                <Button size="sm" variant="outline" className="gap-2" onClick={() => setInvoiceOpen(true)}>
                  <Pencil className="h-4 w-4" />
                  Edit
                </Button>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="text-slate-500">Authors</div>
                <div className="text-slate-900">{invAuthors || '—'}</div>
                <div className="text-slate-500 pt-2">Affiliation</div>
                <div className="text-slate-900">{invAffiliation || '—'}</div>
                <div className="text-slate-500 pt-2">APC Amount</div>
                <div className="text-slate-900">{invApc || '—'}</div>
                <div className="text-slate-500 pt-2">Funding Info</div>
                <div className="text-slate-900 whitespace-pre-wrap">{invFunding || '—'}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Status Transition</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {nextStatuses.length === 0 ? (
                  <div className="text-sm text-slate-500">No next actions available.</div>
                ) : (
                  nextStatuses.map((s) => (
                    <Button
                      key={s}
                      className="w-full justify-between"
                      variant="outline"
                      disabled={transitioning === s}
                      onClick={async () => {
                        try {
                          setTransitioning(s)
                          const res = await EditorApi.patchManuscriptStatus(id, s)
                          if (!res?.success) throw new Error(res?.detail || res?.message || 'Transition failed')
                          toast.success(`Moved to ${getStatusLabel(s)}`)
                          await load()
                        } catch (e) {
                          toast.error(e instanceof Error ? e.message : 'Transition failed')
                        } finally {
                          setTransitioning(null)
                        }
                      }}
                    >
                      <span>Move to {getStatusLabel(s)}</span>
                      {transitioning === s ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    </Button>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      <Dialog open={invoiceOpen} onOpenChange={setInvoiceOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit Invoice Info</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Authors" value={invAuthors} onChange={(e) => setInvAuthors(e.target.value)} />
            <Input placeholder="Affiliation" value={invAffiliation} onChange={(e) => setInvAffiliation(e.target.value)} />
            <Input placeholder="APC Amount" value={invApc} onChange={(e) => setInvApc(e.target.value)} />
            <Textarea
              placeholder="Funding Info"
              value={invFunding}
              onChange={(e) => setInvFunding(e.target.value)}
            />

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setInvoiceOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={invoiceSaving}
                onClick={async () => {
                  try {
                    setInvoiceSaving(true)
                    const apc = invApc.trim() ? Number(invApc) : undefined
                    const res = await EditorApi.updateInvoiceInfo(id, {
                      authors: invAuthors || undefined,
                      affiliation: invAffiliation || undefined,
                      apc_amount: Number.isFinite(apc as number) ? (apc as number) : undefined,
                      funding_info: invFunding || undefined,
                    })
                    if (!res?.success) throw new Error(res?.detail || res?.message || 'Save failed')
                    toast.success('Invoice info updated')
                    setInvoiceOpen(false)
                    await load()
                  } catch (e) {
                    toast.error(e instanceof Error ? e.message : 'Save failed')
                  } finally {
                    setInvoiceSaving(false)
                  }
                }}
              >
                {invoiceSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
