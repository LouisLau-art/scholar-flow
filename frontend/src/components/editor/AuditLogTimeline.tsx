'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { EditorApi } from '@/services/editorApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { Activity } from 'lucide-react'
import type { InternalTask, InternalTaskActivity } from '@/types/internal-collaboration'

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

type TimelineCategory = 'all' | 'status' | 'author' | 'reviewer' | 'internal' | 'task'

interface TimelineEvent {
  id: string
  category: Exclude<TimelineCategory, 'all'>
  createdAt: string
  title: string
  actor?: string
  meta?: string
  content?: string
}

interface TimelineContextPayload {
  audit_logs?: AuditLog[]
  comments?: InternalCommentItem[]
  tasks?: InternalTask[]
  task_activities?: Array<InternalTaskActivity & { task_title?: string | null }>
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

function actorName(user?: { full_name?: string | null; email?: string | null } | null): string {
  return String(user?.full_name || user?.email || 'System').trim() || 'System'
}

function taskActionLabel(action: string): string {
  const normalized = String(action || '').trim().toLowerCase()
  if (normalized === 'task_created') return '内部任务创建'
  if (normalized === 'status_changed') return '内部任务状态变更'
  if (normalized === 'assignee_changed') return '内部任务指派变更'
  if (normalized === 'due_at_changed') return '内部任务截止时间调整'
  if (normalized === 'task_updated') return '内部任务更新'
  return normalized || '内部任务事件'
}

function taskStatusLabel(value: unknown): string {
  const status = String(value || '').trim().toLowerCase()
  if (!status) return ''
  if (status === 'todo') return 'To Do'
  if (status === 'in_progress') return 'In Progress'
  if (status === 'done') return 'Done'
  return status
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
  const rootRef = useRef<HTMLDivElement | null>(null)
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [comments, setComments] = useState<InternalCommentItem[]>([])
  const [tasks, setTasks] = useState<InternalTask[]>([])
  const [taskActivities, setTaskActivities] = useState<
    Array<InternalTaskActivity & { task_title?: string | null }>
  >([])
  const [category, setCategory] = useState<TimelineCategory>('all')
  const [loading, setLoading] = useState(true)
  const [activated, setActivated] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [reloadNonce, setReloadNonce] = useState(0)

  const getActionLabel = (log: AuditLog) => {
    const action = String(log.payload?.action || '')
    if (!action.startsWith('precheck_')) return null
    const decision = log.payload?.decision ? ` (${log.payload?.decision})` : ''
    return `${action}${decision}`
  }

  useEffect(() => {
    setActivated(false)
  }, [manuscriptId])

  useEffect(() => {
    if (activated) return
    const node = rootRef.current
    if (!node || typeof IntersectionObserver === 'undefined') {
      setActivated(true)
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setActivated(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px 0px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [activated])

  useEffect(() => {
    if (!activated) {
      setLoading(false)
      return
    }
    let mounted = true
    setLoading(true)
    setLoadError(null)
    setTaskActivities([])
    EditorApi.getTimelineContext(manuscriptId, { taskLimit: 50, activityLimit: 500 })
      .then((ctxRes) => {
        if (!mounted) return
        const payload: TimelineContextPayload | null = ctxRes?.success ? (ctxRes.data as TimelineContextPayload) : null
        const auditRows = Array.isArray(payload?.audit_logs) ? payload.audit_logs : []
        const commentRows = Array.isArray(payload?.comments) ? payload.comments : []
        const taskRows: InternalTask[] = Array.isArray(payload?.tasks) ? payload.tasks : []
        setTasks(taskRows)
        const activityRows: Array<InternalTaskActivity & { task_title?: string | null }> = Array.isArray(
          payload?.task_activities
        )
          ? payload.task_activities
          : []
        setLogs(auditRows)
        setComments(commentRows)
        setTaskActivities(activityRows)
      })
      .catch(() => {
        if (!mounted) return
        setLogs([])
        setComments([])
        setTasks([])
        setTaskActivities([])
        setLoadError('Failed to load timeline context.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [activated, manuscriptId, reloadNonce])

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

    for (const activity of taskActivities) {
      if (!isValidDate(activity.created_at)) continue
      const beforeStatus = taskStatusLabel(activity.before_payload?.status)
      const afterStatus = taskStatusLabel(activity.after_payload?.status)
      const statusMeta =
        activity.action === 'status_changed' && (beforeStatus || afterStatus)
          ? `${beforeStatus || '—'} -> ${afterStatus || '—'}`
          : undefined
      const taskTitle = normalizeText(activity.task_title || '')
      merged.push({
        id: `task-activity-${activity.id}`,
        category: 'task',
        createdAt: activity.created_at,
        title: taskActionLabel(activity.action),
        actor: actorName(activity.actor),
        meta: statusMeta,
        content: taskTitle ? `任务: ${taskTitle}` : undefined,
      })
    }

    // 兜底：若某些任务没有 activity 记录，至少显示任务创建事件。
    const activityTaskIds = new Set(taskActivities.map((item) => String(item.task_id || '')))
    for (const task of tasks) {
      if (!isValidDate(task.created_at)) continue
      if (activityTaskIds.has(String(task.id || ''))) continue
      merged.push({
        id: `task-created-fallback-${task.id}`,
        category: 'task',
        createdAt: String(task.created_at),
        title: '内部任务创建',
        actor: actorName(task.creator || null),
        meta: taskStatusLabel(task.status),
        content: normalizeText(task.title),
      })
    }

    return merged.sort((a, b) => {
      const at = new Date(a.createdAt).getTime()
      const bt = new Date(b.createdAt).getTime()
      return bt - at
    })
  }, [authorResponses, comments, logs, reviewerInvites, taskActivities, tasks])

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
      task: events.filter((item) => item.category === 'task').length,
    }
  }, [events])

  const dotClass = (eventCategory: TimelineEvent['category']) => {
    if (eventCategory === 'status') return 'bg-primary'
    if (eventCategory === 'author') return 'bg-violet-500'
    if (eventCategory === 'reviewer') return 'bg-emerald-500'
    if (eventCategory === 'task') return 'bg-cyan-500'
    return 'bg-amber-500'
  }

  return (
    <Card ref={rootRef} className="shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-foreground">
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
          <Button size="sm" variant={category === 'task' ? 'secondary' : 'outline'} onClick={() => setCategory('task')}>
            Task ({categoryCount.task})
          </Button>
        </div>

        <div className="relative pl-4 border-l-2 border-border/60 space-y-6 max-h-[520px] overflow-auto pr-1">
          {!activated ? <div className="text-xs text-muted-foreground">Timeline will load when visible.</div> : null}
          {loading ? <div className="text-xs text-muted-foreground">Loading timeline...</div> : null}
          {!loading && loadError ? (
            <div className="space-y-2">
              <div className="text-xs text-rose-600">{loadError}</div>
              <Button size="sm" variant="outline" onClick={() => setReloadNonce((prev) => prev + 1)}>
                Retry
              </Button>
            </div>
          ) : null}
          {!loading && filteredEvents.map((event, idx) => (
            <div key={event.id} className={`relative ${idx > 0 ? 'opacity-90' : ''}`}>
              <div className={`absolute -left-[21px] top-1 w-3 h-3 rounded-full border-2 border-background ${dotClass(event.category)}`}></div>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="text-sm font-medium text-foreground">{event.title}</div>
                <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
                  {event.category}
                </Badge>
                {event.meta ? (
                  <Badge variant="secondary" className="text-[10px]">
                    {event.meta}
                  </Badge>
                ) : null}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {format(new Date(event.createdAt), 'yyyy-MM-dd HH:mm')}
                {event.actor ? ` by ${event.actor}` : ''}
              </div>
              {event.content ? (
                <div className="text-xs text-foreground mt-1 bg-muted/50 p-2 rounded border border-border/60 whitespace-pre-wrap">
                  {event.content}
                </div>
              ) : null}
            </div>
          ))}
          {!loading && !loadError && filteredEvents.length === 0 ? <div className="text-xs text-muted-foreground">No timeline events.</div> : null}
        </div>
      </CardContent>
    </Card>
  )
}
