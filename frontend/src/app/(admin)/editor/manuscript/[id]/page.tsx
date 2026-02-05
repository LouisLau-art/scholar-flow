'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { EditorApi } from '@/services/editorApi'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { InvoiceInfoModal, type InvoiceInfoForm } from '@/components/editor/InvoiceInfoModal'
import { ReviewerAssignmentSearch } from '@/components/editor/ReviewerAssignmentSearch'
import { ProductionStatusCard } from '@/components/editor/ProductionStatusCard'
import VersionHistory from '@/components/VersionHistory'
import { getStatusLabel } from '@/lib/statusStyles'
import { ManuscriptHeader } from '@/components/editor/ManuscriptHeader'
import { FileSectionCard, type FileCardItem } from '@/components/editor/FileSectionCard'
import { UploadReviewFile } from '@/components/editor/UploadReviewFile'
import { InvoiceInfoPanel } from '@/components/editor/InvoiceInfoPanel'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { filterFilesByType, type ManuscriptFile } from './utils'

type ManuscriptDetail = {
  id: string
  title?: string | null
  abstract?: string | null
  status?: string | null
  updated_at?: string | null
  final_pdf_path?: string | null
  owner?: { full_name?: string | null; email?: string | null } | null
  editor?: { full_name?: string | null; email?: string | null } | null
  invoice_metadata?: { authors?: string; affiliation?: string; apc_amount?: number; funding_info?: string } | null
  invoice?: { status?: string | null; amount?: number | string | null } | null
  signed_files?: {
    original_manuscript?: { signed_url?: string | null; path?: string | null }
    peer_review_reports?: Array<{
      review_report_id: string
      reviewer_name?: string | null
      reviewer_email?: string | null
      reviewer_id?: string | null
      signed_url?: string | null
      path?: string | null
    }>
  }
  files?: ManuscriptFile[] | null
}

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
  const [transitioning, setTransitioning] = useState<string | null>(null)

  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [invoiceForm, setInvoiceForm] = useState<InvoiceInfoForm>({
    authors: '',
    affiliation: '',
    apcAmount: '',
    fundingInfo: '',
  })
  const [invoiceSaving, setInvoiceSaving] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const detailRes = await EditorApi.getManuscriptDetail(id)
      if (!detailRes?.success) throw new Error(detailRes?.detail || detailRes?.message || 'Manuscript not found')
      const detail = detailRes.data
      setMs(detail)

      const meta = (detail?.invoice_metadata as any) || {}
      setInvoiceForm({
        authors: String(meta.authors || ''),
        affiliation: String(meta.affiliation || ''),
        apcAmount: meta.apc_amount != null ? String(meta.apc_amount) : '',
        fundingInfo: String(meta.funding_info || ''),
      })
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
  const statusLower = status.toLowerCase()
  const isPostAcceptance = ['approved', 'layout', 'english_editing', 'proofreading', 'published'].includes(statusLower)
  const nextStatuses = useMemo(() => allowedNext(status), [status])
  const pdfSignedUrl = ms?.signed_files?.original_manuscript?.signed_url || null

  const coverFiles = useMemo(() => filterFilesByType(ms?.files || [], 'cover_letter'), [ms])
  const originalFiles = useMemo(() => filterFilesByType(ms?.files || [], 'manuscript'), [ms])
  const reviewFiles = useMemo(() => filterFilesByType(ms?.files || [], 'review_attachment'), [ms])

  const toItems = (files: ManuscriptFile[], fallbackEmptyLabel: string): FileCardItem[] => {
    return (files || [])
      .filter((f) => !!f?.signed_url)
      .map((f) => ({
        id: String(f.id),
        label: String(f.label || fallbackEmptyLabel),
        href: f.signed_url || undefined,
        meta: f.path ? `Storage: ${f.path}` : null,
      }))
  }

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
        <ManuscriptHeader ms={ms as any} />

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

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <FileSectionCard
                title="Cover Letter"
                description="Author-provided materials (if any)."
                items={toItems(coverFiles, 'Cover Letter')}
                emptyText="No cover letter uploaded."
              />

              <FileSectionCard
                title="Original Manuscript"
                description="Current manuscript file (signed URL)."
                items={toItems(originalFiles, 'Manuscript PDF')}
                emptyText="PDF not available."
              />

              <FileSectionCard
                title="Peer Review Files"
                description="Editor-only internal files (Word/PDF) + reviewer attachments."
                items={toItems(reviewFiles, 'Peer Review File')}
                emptyText="No peer review files."
                action={<UploadReviewFile manuscriptId={id} onUploaded={load} />}
              />
            </div>

            <VersionHistory manuscriptId={id} />
          </div>

          <div className="lg:col-span-4 space-y-6">
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-lg">Owner Binding</CardTitle>
                <BindingOwnerDropdown manuscriptId={id} currentOwner={ms.owner as any} onBound={load} />
              </CardHeader>
              <CardContent className="text-sm text-slate-600 space-y-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Current Owner</span>
                  <span className="text-slate-900">{ms.owner?.full_name || ms.owner?.email || '—'}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Workflow</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Current Status</span>
                  <span className="text-slate-900">{getStatusLabel(status)}</span>
                </div>
                <div className="pt-2">
                  <ReviewerAssignmentSearch manuscriptId={id} onChanged={load} />
                  <div className="mt-2 text-xs text-slate-500">
                    从 Reviewer Library 搜索并指派；已分配的审稿人会在弹窗中置顶显示。
                  </div>
                </div>
              </CardContent>
            </Card>

            {isPostAcceptance ? (
              <ProductionStatusCard
                manuscriptId={id}
                status={statusLower || 'approved'}
                finalPdfPath={ms?.final_pdf_path}
                invoice={ms?.invoice}
                onStatusChange={(next) => {
                  setMs((prev) => (prev ? { ...prev, status: next } : prev))
                }}
                onReload={async () => {
                  await load()
                }}
              />
            ) : null}

            {!isPostAcceptance ? (
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
            ) : null}
          </div>
        </div>

        <InvoiceInfoPanel
          info={{
            authors: invoiceForm.authors,
            affiliation: invoiceForm.affiliation,
            apcAmount: invoiceForm.apcAmount,
            fundingInfo: invoiceForm.fundingInfo,
          }}
          onEdit={() => setInvoiceOpen(true)}
        />
      </main>

      <InvoiceInfoModal
        open={invoiceOpen}
        onOpenChange={setInvoiceOpen}
        form={invoiceForm}
        onChange={(patch) => setInvoiceForm((prev) => ({ ...prev, ...patch }))}
        saving={invoiceSaving}
        onSave={async () => {
          try {
            setInvoiceSaving(true)
            const apc = invoiceForm.apcAmount.trim() ? Number(invoiceForm.apcAmount) : undefined
            const res = await EditorApi.updateInvoiceInfo(id, {
              authors: invoiceForm.authors || undefined,
              affiliation: invoiceForm.affiliation || undefined,
              apc_amount: Number.isFinite(apc as number) ? (apc as number) : undefined,
              funding_info: invoiceForm.fundingInfo || undefined,
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
      />
    </div>
  )
}
