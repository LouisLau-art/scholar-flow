'use client'

import { useEffect, useMemo, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { ProductionWorkspacePanel } from '@/components/editor/production/ProductionWorkspacePanel'
import { ProductionActionPanel } from '@/components/editor/production/ProductionActionPanel'
import { ProductionTimeline } from '@/components/editor/production/ProductionTimeline'
import { AuthorEmailPreviewDialog } from '@/components/editor/AuthorEmailPreviewDialog'
import type { ProductionWorkspaceContext } from '@/types/production'
import type { AuthorEmailPreviewData } from '@/services/editor-api/types'
import { normalizeApiErrorMessage } from '@/lib/normalizeApiError'

type StaffOption = {
  id: string
  name: string
  email?: string | null
  roles?: string[] | null
}

function normalizeRecipientEmails(value: string): string[] {
  const normalized = String(value || '')
    .replace(/;/g, ',')
    .replace(/\n/g, ',')
  const parts = normalized
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
  return Array.from(new Set(parts))
}

function normalizeEmailListInput(value: string): string[] {
  return normalizeRecipientEmails(value)
}

export default function EditorProductionWorkspacePage() {
  const params = useParams()
  const manuscriptId = String((params as Record<string, string>)?.id || '')

  const [loading, setLoading] = useState(true)
  const [context, setContext] = useState<ProductionWorkspaceContext | null>(null)
  const [staff, setStaff] = useState<StaffOption[]>([])

  const [emailPreviewOpen, setEmailPreviewOpen] = useState(false)
  const [emailPreviewLoading, setEmailPreviewLoading] = useState(false)
  const [emailPreviewSending, setEmailPreviewSending] = useState(false)
  const [emailPreviewData, setEmailPreviewData] = useState<AuthorEmailPreviewData | null>(null)
  const [emailPreviewRecipient, setEmailPreviewRecipient] = useState('')
  const [emailPreviewCc, setEmailPreviewCc] = useState('')
  const [emailPreviewReplyTo, setEmailPreviewReplyTo] = useState('')
  const [emailPreviewSubject, setEmailPreviewSubject] = useState('')
  const [emailPreviewHtml, setEmailPreviewHtml] = useState('')

  const handleOpenProofreadingEmail = useCallback(async () => {
    if (!context?.active_cycle?.id) return
    setEmailPreviewOpen(true)
    setEmailPreviewLoading(true)
    try {
      const res = await EditorApi.previewProofreadingEmail(manuscriptId, context.active_cycle.id, { editor_message: '' })
      if (!res?.success) throw new Error(normalizeApiErrorMessage(res, 'Failed to preview proofreading email'))
      const preview = res.data as AuthorEmailPreviewData
      setEmailPreviewData(preview)
      setEmailPreviewRecipient(String(preview.recipient_email || '').trim())
      setEmailPreviewCc((preview.resolved_recipients?.cc || []).join(', '))
      setEmailPreviewReplyTo((preview.resolved_recipients?.reply_to || []).join(', '))
      setEmailPreviewSubject(String(preview.subject || '').trim())
      setEmailPreviewHtml(String(preview.html || '').trim())
    } catch (e) {
      setEmailPreviewOpen(false)
      toast.error(e instanceof Error ? e.message : 'Failed to preview proofreading email')
    } finally {
      setEmailPreviewLoading(false)
    }
  }, [manuscriptId, context?.active_cycle?.id])

  const handleCloseEmailPreview = useCallback(() => {
    if (emailPreviewSending) return
    setEmailPreviewOpen(false)
    setEmailPreviewData(null)
  }, [emailPreviewSending])

  const handleSendEmail = useCallback(async () => {
    if (!context?.active_cycle?.id) return
    const recipientEmail = String(emailPreviewRecipient || '').trim()
    const ccEmails = emailPreviewCc.replace(/;/g, ',').split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
    const replyToEmails = emailPreviewReplyTo.replace(/;/g, ',').split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
    const subjectOverride = String(emailPreviewSubject || '').trim()
    const bodyHtmlOverride = String(emailPreviewHtml || '').trim()
    
    if (!recipientEmail || !subjectOverride || !bodyHtmlOverride) {
      toast.error('Recipient, Subject, and Body are required.')
      return
    }

    setEmailPreviewSending(true)
    try {
      const payload = {
        recipient_email: recipientEmail,
        cc_emails: ccEmails,
        reply_to_emails: replyToEmails,
        subject_override: subjectOverride,
        body_html_override: bodyHtmlOverride,
      }
      const res = await EditorApi.sendProofreadingEmail(manuscriptId, context.active_cycle.id, payload)
      if (!res?.success) throw new Error(normalizeApiErrorMessage(res, 'Failed to send proofreading email'))
      
      const isPreview = Boolean(res?.data?.preview_send)
      if (isPreview) {
        toast.success(`Preview email sent to ${recipientEmail}.`)
      } else {
        toast.success(`Proofreading reminder sent successfully.`)
        // maybe reload context
      }
      handleCloseEmailPreview()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to send proofreading email')
    } finally {
      setEmailPreviewSending(false)
    }
  }, [context?.active_cycle?.id, emailPreviewRecipient, emailPreviewCc, emailPreviewReplyTo, emailPreviewSubject, emailPreviewHtml, manuscriptId, handleCloseEmailPreview])

  const handleMarkExternalSentEmail = useCallback(async () => {
    if (!context?.active_cycle?.id) return
    
    setEmailPreviewSending(true)
    try {
      const res = await EditorApi.markProofreadingEmailExternalSent(manuscriptId, context.active_cycle.id, { note: 'Sent manually by editor via external system' })
      if (!res?.success) throw new Error(normalizeApiErrorMessage(res, 'Failed to mark as sent externally'))
      
      toast.success('Successfully marked as sent externally.')
      handleCloseEmailPreview()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to mark as sent externally')
    } finally {
      setEmailPreviewSending(false)
    }
  }, [context?.active_cycle?.id, manuscriptId, handleCloseEmailPreview])

  const load = async () => {
    setLoading(true)
    try {
      const [ctxRes, staffRes] = await Promise.all([
        EditorApi.getProductionWorkspaceContext(manuscriptId),
        EditorApi.listInternalStaff(''),
      ])

      if (!ctxRes?.success || !ctxRes?.data) {
        throw new Error(ctxRes?.detail || ctxRes?.message || 'Failed to load production workspace')
      }

      const staffRows = (staffRes?.data || []) as Array<Record<string, any>>
      const options: StaffOption[] = staffRows.map((item) => ({
        id: String(item.id || ''),
        name: String(item.full_name || item.name || item.email || item.id || ''),
        email: item.email ? String(item.email) : null,
        roles: Array.isArray(item.roles) ? (item.roles as string[]) : null,
      }))

      setContext(ctxRes.data as ProductionWorkspaceContext)
      setStaff(options)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load production workspace')
      setContext(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!manuscriptId) return
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  const previewUrl = useMemo(() => {
    if (!context) return null
    return context.active_cycle?.galley_signed_url || context.manuscript.pdf_url || null
  }, [context])

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </main>
    )
  }

  if (!context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40 px-6 text-sm text-muted-foreground">
        Production workspace is unavailable for this manuscript.
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-muted/40">
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex sf-max-w-1700 items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Production Pipeline Workspace</p>
            <h1 className="truncate text-lg font-semibold text-foreground sm:text-xl">{context.manuscript.title || 'Untitled Manuscript'}</h1>
            <p className="text-xs text-muted-foreground">Current status: {context.manuscript.status || '--'}</p>
          </div>
          <Link
            href={`/editor/manuscript/${encodeURIComponent(manuscriptId)}`}
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            返回稿件详情
          </Link>
        </div>
      </header>

      <div className="mx-auto grid sf-max-w-1700 grid-cols-1 gap-4 px-4 py-4 md:grid-cols-12 sm:px-6">
        <section className="md:col-span-5 lg:col-span-5">
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            {previewUrl ? (
              <iframe
                title="Production Workspace PDF Preview"
                src={previewUrl}
                className="h-[calc(100vh-140px)] min-h-[520px] w-full"
              />
            ) : (
              <div className="flex h-[calc(100vh-140px)] min-h-[520px] items-center justify-center text-sm text-muted-foreground">
                PDF preview is unavailable.
              </div>
            )}
          </div>
        </section>

        <section className="space-y-3 md:col-span-4 lg:col-span-4">
          <ProductionTimeline cycles={context.cycle_history || []} />
        </section>

        <section className="space-y-3 md:col-span-3 lg:col-span-3">
          <ProductionWorkspacePanel manuscriptId={manuscriptId} context={context} staff={staff} onReload={load} />
          <ProductionActionPanel
            manuscriptId={manuscriptId}
            activeCycle={context.active_cycle || null}
            canApprove={Boolean(context.permissions?.can_approve)}
            onApproved={load}
            onOpenProofreadingEmail={handleOpenProofreadingEmail}
          />
        </section>
      </div>

      <AuthorEmailPreviewDialog
        open={emailPreviewOpen}
        title="Preview Proofreading Reminder Email"
        description="发送清样校对提醒邮件给作者。"
        loading={emailPreviewLoading}
        sending={emailPreviewSending}
        preview={emailPreviewData}
        recipientEmail={emailPreviewRecipient}
        ccValue={emailPreviewCc}
        replyToValue={emailPreviewReplyTo}
        subjectValue={emailPreviewSubject}
        htmlValue={emailPreviewHtml}
        onSubjectChange={setEmailPreviewSubject}
        onHtmlChange={setEmailPreviewHtml}
        onRecipientEmailChange={setEmailPreviewRecipient}
        onCcChange={setEmailPreviewCc}
        onReplyToChange={setEmailPreviewReplyTo}
        onClose={handleCloseEmailPreview}
        onSend={handleSendEmail}
        onMarkExternalSent={handleMarkExternalSentEmail}
      />
    </main>
  )
}
