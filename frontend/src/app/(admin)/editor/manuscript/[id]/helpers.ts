import { format } from 'date-fns'

import { type EditorCapability } from '@/lib/rbac'
import type { FileItem } from '@/components/editor/FileHubCard'
import { filterFilesByType, type ManuscriptFile } from './utils'

export type ManuscriptDetail = {
  id: string
  title?: string | null
  abstract?: string | null
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
  final_pdf_path?: string | null
  author?: { full_name?: string | null; email?: string | null; affiliation?: string | null } | null
  owner?: { full_name?: string | null; email?: string | null } | null
  editor?: { id?: string | null; full_name?: string | null; email?: string | null } | null
  assistant_editor?: { id?: string | null; full_name?: string | null; email?: string | null } | null
  assistant_editor_id?: string | null
  invoice_metadata?: { authors?: string; affiliation?: string; apc_amount?: number; funding_info?: string } | null
  invoice?: { status?: string | null; amount?: number | string | null } | null
  signed_files?: any
  files?: ManuscriptFile[] | null
  journals?: { title?: string } | null
  role_queue?: {
    current_role?: string | null
    current_assignee?: { id: string; full_name?: string | null; email?: string | null } | null
    current_assignee_label?: string | null
    assigned_at?: string | null
    technical_completed_at?: string | null
    academic_completed_at?: string | null
  } | null
  precheck_timeline?: Array<{
    id: string
    created_at?: string | null
    payload?: { action?: string; decision?: string } | null
    comment?: string | null
  }> | null
  reviewer_invites?: Array<{
    id: string
    reviewer_name?: string | null
    reviewer_email?: string | null
    status: string
    due_at?: string | null
    invited_at?: string | null
    opened_at?: string | null
    accepted_at?: string | null
    declined_at?: string | null
    submitted_at?: string | null
    decline_reason?: string | null
  }> | null
  task_summary?: {
    open_tasks_count?: number
    overdue_tasks_count?: number
    is_overdue?: boolean
    nearest_due_at?: string | null
  } | null
  author_response_history?: Array<{
    id?: string | null
    response_letter?: string | null
    submitted_at?: string | null
    round?: number | null
  }> | null
  latest_author_response_letter?: string | null
  latest_author_response_submitted_at?: string | null
  latest_author_response_round?: number | null
}

export type AuthorResponseHistoryItem = {
  id: string
  text: string
  submittedAt: string | null
  round: number | null
}

export function normalizeResponseLetterText(raw: unknown): string {
  const source = String(raw || '').trim()
  if (!source) return ''
  return source
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

export function allowedNext(status: string): string[] {
  const s = (status || '').toLowerCase()
  if (s === 'pre_check') return ['under_review', 'minor_revision']
  if (s === 'under_review') return ['decision']
  if (s === 'resubmitted') return ['under_review', 'decision']
  if (s === 'decision') return ['decision_done']
  if (s === 'decision_done') return ['approved', 'major_revision', 'minor_revision', 'rejected']
  return []
}

export function getNextActionCard(
  manuscript: ManuscriptDetail,
  capability: EditorCapability
): { phase: string; title: string; description: string; blockers: string[] } {
  const status = String(manuscript.status || '').toLowerCase()
  const blockers: string[] = []
  const amount = Number(manuscript.invoice?.amount ?? manuscript.invoice_metadata?.apc_amount ?? 0)
  const invoiceStatus = String(manuscript.invoice?.status || '').toLowerCase()

  if (status === 'pre_check') {
    return {
      phase: 'Pre-check',
      title: '先完成入口技术审查，再决定分配 AE 或退回作者',
      description: '当前阶段不应直接进入终审动作。请先确认材料完整性与格式规范。',
      blockers,
    }
  }

  if (status === 'under_review' || status === 'resubmitted') {
    if ((manuscript.reviewer_invites || []).length === 0) blockers.push('尚未发出审稿邀请')
    return {
      phase: 'External Review',
      title: '推进外审并收集可决策意见',
      description: 'AE 需跟进邀请接受率与审稿提交率，达到阈值后进入 Decision。',
      blockers,
    }
  }

  if (status === 'decision' || status === 'decision_done') {
    if (!(capability.canRecordFirstDecision || capability.canSubmitFinalDecision)) {
      blockers.push('当前账号无决策权限')
    }
    return {
      phase: 'Decision',
      title: '在 Decision Workspace 完成首轮/终轮学术决策',
      description: '请确保审稿依据充分并写明决策理由，关键状态流转需保留审计痕迹。',
      blockers,
    }
  }

  if (['approved', 'layout', 'english_editing', 'proofreading'].includes(status)) {
    if (amount > 0 && invoiceStatus !== 'paid') blockers.push('Payment Gate 未满足（发票未确认 paid）')
    if (!manuscript.final_pdf_path) blockers.push('Proof Gate 未满足（final PDF 尚未上传）')
    return {
      phase: 'Production',
      title: '并行推进 Production 与 Finance，满足双门禁后发布',
      description: '发布前必须同时满足付款确认与校对完成条件。',
      blockers,
    }
  }

  if (status === 'published') {
    return {
      phase: 'Published',
      title: '稿件已发布',
      description: '当前进入公开传播阶段，可继续跟踪下载与引用。',
      blockers,
    }
  }

  return {
    phase: 'Workflow',
    title: '请按当前状态继续推进流程',
    description: '若出现状态异常，请先在审计日志核对最近一次流转。',
    blockers,
  }
}

export function buildAuthorResponseHistory(manuscript: ManuscriptDetail | null): AuthorResponseHistoryItem[] {
  const rawHistory = Array.isArray(manuscript?.author_response_history) ? manuscript.author_response_history : []
  const normalized = rawHistory
    .map((item, idx) => {
      const text = normalizeResponseLetterText(item?.response_letter)
      if (!text) return null
      const rawRound = item?.round
      const round = typeof rawRound === 'number' ? rawRound : rawRound != null ? Number(rawRound) : null
      return {
        id: String(item?.id || `response-${idx}`),
        text,
        submittedAt: item?.submitted_at || null,
        round: Number.isFinite(round as number) ? (round as number) : null,
      }
    })
    .filter((item): item is AuthorResponseHistoryItem => Boolean(item))

  if (normalized.length > 0) return normalized

  const fallbackText = normalizeResponseLetterText(manuscript?.latest_author_response_letter)
  if (!fallbackText) return []
  return [
    {
      id: 'latest-fallback',
      text: fallbackText,
      submittedAt: manuscript?.latest_author_response_submitted_at || null,
      round: typeof manuscript?.latest_author_response_round === 'number' ? manuscript.latest_author_response_round : null,
    },
  ]
}

function mapFile(f: ManuscriptFile, type: FileItem['type']): FileItem {
  const visual = inferFileVisual(f, type)
  return {
    id: String(f.id),
    label: f.label || f.original_filename || f.path || 'Unknown File',
    type: visual.type,
    badge: visual.badge,
    url: f.signed_url || undefined,
    date: f.created_at ? format(new Date(f.created_at), 'yyyy-MM-dd') : undefined,
  }
}

function getFileExtension(file: ManuscriptFile): string {
  const candidates = [
    String(file.original_filename || ''),
    String(file.label || ''),
    String(file.path || ''),
    String(file.signed_url || ''),
  ]
  for (const candidate of candidates) {
    const m = candidate.toLowerCase().match(/\.([a-z0-9]{1,8})(?:[?#].*)?$/)
    if (m?.[1]) return m[1]
  }
  return ''
}

function inferFileVisual(
  file: ManuscriptFile,
  fallbackType: FileItem['type']
): { type: FileItem['type']; badge: string } {
  const ext = getFileExtension(file)
  const contentType = String(file.content_type || '').toLowerCase()

  if (ext === 'pdf' || contentType.includes('application/pdf')) {
    return { type: 'pdf', badge: 'PDF' }
  }
  if (
    ['doc', 'docx', 'rtf', 'odt'].includes(ext) ||
    contentType.includes('msword') ||
    contentType.includes('wordprocessingml')
  ) {
    return { type: 'doc', badge: ext ? ext.toUpperCase() : 'DOC' }
  }
  if (['txt', 'md'].includes(ext) || contentType.startsWith('text/')) {
    return { type: 'doc', badge: ext ? ext.toUpperCase() : 'TXT' }
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext) || contentType.startsWith('image/')) {
    return { type: 'other', badge: 'IMG' }
  }
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
    return { type: 'other', badge: 'ZIP' }
  }
  if (['xls', 'xlsx', 'csv'].includes(ext)) {
    return { type: 'other', badge: ext.toUpperCase() }
  }
  if (['ppt', 'pptx'].includes(ext)) {
    return { type: 'other', badge: ext.toUpperCase() }
  }

  if (fallbackType === 'rpt') return { type: 'rpt', badge: 'RPT' }
  if (fallbackType === 'pdf') return { type: 'pdf', badge: 'PDF' }
  if (fallbackType === 'doc') return { type: 'doc', badge: 'DOC' }
  return { type: 'other', badge: 'FILE' }
}

export function buildFileHubProps(files?: ManuscriptFile[] | null): {
  manuscriptFiles: FileItem[]
  coverFiles: FileItem[]
  reviewFiles: FileItem[]
} {
  const rawFiles = files || []
  return {
    manuscriptFiles: filterFilesByType(rawFiles, 'manuscript').map((f) => mapFile(f, 'pdf')),
    coverFiles: filterFilesByType(rawFiles, 'cover_letter').map((f) => mapFile(f, 'doc')),
    reviewFiles: filterFilesByType(rawFiles, 'review_attachment').map((f) => mapFile(f, 'rpt')),
  }
}
