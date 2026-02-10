'use client'

import { useEffect, useMemo, useState } from 'react'
import { EditorApi } from '@/services/editorApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { Activity } from 'lucide-react'

interface AuditLog {
  id: string
  from_status: string
  to_status: string
  comment: string | null
  created_at: string
  payload?: {
    action?: string
    decision?: string
  } | null
  user?: {
    full_name?: string
    email?: string
  }
}

interface AuthorResponseItem {
  id: string
  text: string
  submittedAt: string | null
  round: number | null
}

interface ReviewerInviteItem {
  id: string
  reviewer_name?: string | null
  reviewer_email?: string | null
  due_at?: string | null
  invited_at?: string | null
  opened_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  submitted_at?: string | null
  decline_reason?: string | null
}

interface InternalCommentItem {
  id: string
  content?: string | null
  created_at?: string | null
  user?: {
    full_name?: string | null
    email?: string | null
  } | null
}

type TimelineCategory = 'all' | 'status' | 'author' | 'reviewer' | 'internal'

interface TimelineEvent {
  id: string
  category: Exclude<TimelineCategory, 'all'>
  createdAt: string
  title: string
  actor?: string
  meta?: string
  content?: string
}

interface AuditLogTimelineProps {
  manuscriptId: string
  authorResponses?: AuthorResponseItem[]
  reviewerInvites?: ReviewerInviteItem[]
}

function normalizeText(raw: unknown): string {
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

function statusLabel(raw: unknown): string {
  const value = String(raw || '').trim().toLowerCase()
  if (!value) return 'unknown'
  return value.replace(/_/g, ' ')
}

function actorName(user?: { full_name?: string; email?: string } | null): string {
  return String(user?.full_name || user?.email || 'System').trim() || 'System'
}

function isValidDate(value: unknown): value is string {
  const raw = String(value || '').trim()
  if (!raw) return false
  const d = new Date(raw)
  return !Number.isNaN(d.getTime())
}

export function AuditLogTimeline({
  manuscriptId,
  authorResponses = [],
  reviewerInvites = [],
}: AuditLogTimelineProps) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [comments, setComments] = useState<InternalCommentItem[]>([])
  const [category, setCategory] = useState<TimelineCategory>('all')
  const [loading, setLoading] = useState(true)

  const getActionLabel = (log: AuditLog) => {
    const action = String(log.payload?.action || '')
    if (!action.startsWith('precheck_')) return null
    const decision = log.payload?.decision ? ` (${log.payload?.decision})` : ''
    return `${action}${decision}`
  }

  useEffect(() => {
    let mounted = true
    setLoading(true)
    Promise.all([
      EditorApi.getAuditLogs(manuscriptId),
      EditorApi.getInternalComments(manuscriptId),
    ])
      .then(([auditRes, commentRes]) => {
        if (!mounted) return
        if (auditRes?.success) setLogs(Array.isArray(auditRes.data) ? auditRes.data : [])
        if (commentRes?.success) setComments(Array.isArray(commentRes.data) ? commentRes.data : [])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [manuscriptId])

  const events = useMemo<TimelineEvent[]>(() => {
    const merged: TimelineEvent[] = []

    for (const log of logs) {
      if (!isValidDate(log.created_at)) continue
      const actionLabel = getActionLabel(log)
      merged.push({
        id: `status-${log.id}`,
        category: 'status',
        createdAt: log.created_at,
        title: `状态流转: ${statusLabel(log.from_status)} -> ${statusLabel(log.to_status)}`,
        actor: actorName(log.user),
        meta: actionLabel || undefined,
        content: normalizeText(log.comment),
      })
    }

    for (const item of authorResponses) {
      if (!isValidDate(item.submittedAt)) continue
      merged.push({
        id: `author-response-${item.id}`,
        category: 'author',
        createdAt: item.submittedAt,
        title: '作者提交修回说明',
        actor: 'Author',
        meta: typeof item.round === 'number' ? `Round ${item.round}` : undefined,
        content: normalizeText(item.text),
      })
    }

    for (const invite of reviewerInvites) {
      const reviewer = String(invite.reviewer_name || invite.reviewer_email || 'Reviewer').trim()
      const pushReviewerEvent = (suffix: string, date: string | null | undefined, title: string, content?: string) => {
        if (!isValidDate(date)) return
        merged.push({
          id: `reviewer-${invite.id}-${suffix}`,
          category: 'reviewer',
          createdAt: date,
          title,
          actor: reviewer,
          content: normalizeText(content),
        })
      }
      pushReviewerEvent('invited', invite.invited_at, '发送审稿邀请')
      pushReviewerEvent('opened', invite.opened_at, '审稿人打开邀请')
      pushReviewerEvent('accepted', invite.accepted_at, '审稿人接受邀请')
      pushReviewerEvent('declined', invite.declined_at, '审稿人拒绝邀请', invite.decline_reason || '')
      pushReviewerEvent('submitted', invite.submitted_at, '审稿人提交审稿意见')
      if (isValidDate(invite.due_at)) {
        merged.push({
          id: `reviewer-${invite.id}-due`,
          category: 'reviewer',
          createdAt: invite.due_at,
          title: '审稿截止时间',
          actor: reviewer,
        })
      }
    }

    for (const comment of comments) {
      if (!isValidDate(comment.created_at)) continue
      merged.push({
        id: `internal-comment-${comment.id}`,
        category: 'internal',
        createdAt: comment.created_at || '',
        title: '内部留言',
        actor: actorName(comment.user as { full_name?: string; email?: string } | null),
        content: normalizeText(comment.content),
      })
    }

    return merged.sort((a, b) => {
      const at = new Date(a.createdAt).getTime()
      const bt = new Date(b.createdAt).getTime()
      return bt - at
    })
  }, [authorResponses, comments, logs, reviewerInvites])

  const filteredEvents = useMemo(() => {
    if (category === 'all') return events
    return events.filter((item) => item.category === category)
  }, [category, events])

  const categoryCount = useMemo(() => {
    return {
      all: events.length,
      status: events.filter((item) => item.category === 'status').length,
      author: events.filter((item) => item.category === 'author').length,
      reviewer: events.filter((item) => item.category === 'reviewer').length,
      internal: events.filter((item) => item.category === 'internal').length,
    }
  }, [events])

  const dotClass = (eventCategory: TimelineEvent['category']) => {
    if (eventCategory === 'status') return 'bg-blue-500'
    if (eventCategory === 'author') return 'bg-violet-500'
    if (eventCategory === 'reviewer') return 'bg-emerald-500'
    return 'bg-amber-500'
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
          <Activity className="h-4 w-4" />
          Activity Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <div className="mb-4 flex flex-wrap gap-2">
          <Button size="sm" variant={category === 'all' ? 'secondary' : 'outline'} onClick={() => setCategory('all')}>
            All ({categoryCount.all})
          </Button>
          <Button size="sm" variant={category === 'status' ? 'secondary' : 'outline'} onClick={() => setCategory('status')}>
            Status ({categoryCount.status})
          </Button>
          <Button size="sm" variant={category === 'author' ? 'secondary' : 'outline'} onClick={() => setCategory('author')}>
            Author ({categoryCount.author})
          </Button>
          <Button size="sm" variant={category === 'reviewer' ? 'secondary' : 'outline'} onClick={() => setCategory('reviewer')}>
            Reviewer ({categoryCount.reviewer})
          </Button>
          <Button size="sm" variant={category === 'internal' ? 'secondary' : 'outline'} onClick={() => setCategory('internal')}>
            Internal ({categoryCount.internal})
          </Button>
        </div>

        <div className="relative pl-4 border-l-2 border-slate-100 space-y-6 max-h-[520px] overflow-auto pr-1">
          {loading ? <div className="text-xs text-slate-400">Loading timeline...</div> : null}
          {!loading && filteredEvents.map((event, idx) => (
            <div key={event.id} className={`relative ${idx > 0 ? 'opacity-90' : ''}`}>
              <div className={`absolute -left-[21px] top-1 w-3 h-3 rounded-full border-2 border-white ${dotClass(event.category)}`}></div>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="text-sm font-medium text-slate-900">{event.title}</div>
                <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                  {event.category}
                </Badge>
                {event.meta ? (
                  <Badge variant="secondary" className="text-[10px]">
                    {event.meta}
                  </Badge>
                ) : null}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {format(new Date(event.createdAt), 'yyyy-MM-dd HH:mm')}
                {event.actor ? ` by ${event.actor}` : ''}
              </div>
              {event.content ? (
                <div className="text-xs text-slate-700 mt-1 bg-slate-50 p-2 rounded border border-slate-100 whitespace-pre-wrap">
                  {event.content}
                </div>
              ) : null}
            </div>
          ))}
          {!loading && filteredEvents.length === 0 && <div className="text-xs text-slate-400">No timeline events.</div>}
        </div>
      </CardContent>
    </Card>
  )
}
