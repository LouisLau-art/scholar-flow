'use client'

import { useEffect, useMemo, useState } from 'react'
import { format } from 'date-fns'
import { Loader2, Plus, RefreshCcw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { TaskStatusBadge } from '@/components/editor/TaskStatusBadge'
import { EditorApi } from '@/services/editorApi'
import type {
  CreateInternalTaskPayload,
  InternalTask,
  InternalTaskActivity,
  InternalTaskPriority,
  InternalTaskStatus,
} from '@/types/internal-collaboration'

type StaffOption = {
  id: string
  full_name?: string
  email?: string
}

const PRIORITY_OPTIONS: Array<{ value: InternalTaskPriority; label: string }> = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

const STATUS_OPTIONS: Array<{ value: InternalTaskStatus; label: string }> = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
]

interface InternalTasksPanelProps {
  manuscriptId: string
  onChanged?: () => void
}

function toDateTimeLocalInputValue(date: Date): string {
  const iso = new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000).toISOString()
  return iso.slice(0, 16)
}

function formatTime(value?: string | null): string {
  if (!value) return '—'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '—'
  return format(dt, 'yyyy-MM-dd HH:mm')
}

export function InternalTasksPanel({ manuscriptId, onChanged }: InternalTasksPanelProps) {
  const [tasks, setTasks] = useState<InternalTask[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null)
  const [staff, setStaff] = useState<StaffOption[]>([])
  const [activityByTask, setActivityByTask] = useState<Record<string, InternalTaskActivity[]>>({})
  const [loadingActivityTaskId, setLoadingActivityTaskId] = useState<string | null>(null)
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeUserId, setAssigneeUserId] = useState('')
  const [priority, setPriority] = useState<InternalTaskPriority>('medium')
  const [dueAt, setDueAt] = useState<string>(() => {
    const now = new Date()
    now.setHours(now.getHours() + 24)
    return toDateTimeLocalInputValue(now)
  })

  const orderedTasks = useMemo(
    () =>
      [...tasks].sort((a, b) => {
        const aOverdue = Boolean(a.is_overdue)
        const bOverdue = Boolean(b.is_overdue)
        if (aOverdue !== bOverdue) return aOverdue ? -1 : 1
        return (a.updated_at || '').localeCompare(b.updated_at || '') * -1
      }),
    [tasks]
  )

  async function loadTasks() {
    try {
      setLoading(true)
      const res = await EditorApi.listInternalTasks(manuscriptId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed to load tasks')
      setTasks(Array.isArray(res.data) ? res.data : [])
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  async function loadStaff() {
    try {
      const res = await EditorApi.listInternalStaff('')
      if (!res?.success) return
      const options = Array.isArray(res.data) ? res.data : []
      setStaff(options)
      if (!assigneeUserId && options.length > 0) {
        setAssigneeUserId(String(options[0]?.id || ''))
      }
    } catch {
      // ignore: panel can still work when assignee list failed
    }
  }

  useEffect(() => {
    loadTasks()
    loadStaff()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  async function handleCreateTask() {
    const titleTrimmed = title.trim()
    if (!titleTrimmed) {
      toast.error('Task title is required')
      return
    }
    if (!assigneeUserId) {
      toast.error('Assignee is required')
      return
    }
    if (!dueAt) {
      toast.error('Due time is required')
      return
    }

    const dueIso = new Date(dueAt).toISOString()
    const payload: CreateInternalTaskPayload = {
      title: titleTrimmed,
      description: description.trim() || undefined,
      assignee_user_id: assigneeUserId,
      due_at: dueIso,
      priority,
      status: 'todo',
    }

    try {
      setCreating(true)
      const res = await EditorApi.createInternalTask(manuscriptId, payload)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed to create task')
      const created = res.data as InternalTask
      setTasks((prev) => [created, ...prev])
      setTitle('')
      setDescription('')
      onChanged?.()
      toast.success('Task created')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create task')
    } finally {
      setCreating(false)
    }
  }

  async function handleUpdateStatus(task: InternalTask, status: InternalTaskStatus) {
    if (task.status === status) return
    try {
      setUpdatingTaskId(task.id)
      const res = await EditorApi.patchInternalTask(manuscriptId, task.id, { status })
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed to update task')
      const updated = res.data as InternalTask
      setTasks((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)))
      onChanged?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update task')
    } finally {
      setUpdatingTaskId(null)
    }
  }

  async function toggleActivity(taskId: string) {
    if (expandedTaskId === taskId) {
      setExpandedTaskId(null)
      return
    }
    setExpandedTaskId(taskId)

    if (activityByTask[taskId]) return
    try {
      setLoadingActivityTaskId(taskId)
      const res = await EditorApi.getInternalTaskActivity(manuscriptId, taskId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed to load activity')
      setActivityByTask((prev) => ({ ...prev, [taskId]: Array.isArray(res.data) ? res.data : [] }))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load activity')
    } finally {
      setLoadingActivityTaskId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between gap-4 border-b py-4">
        <CardTitle className="text-sm font-bold uppercase tracking-wide text-slate-700">Internal Tasks</CardTitle>
        <Button variant="outline" size="sm" className="gap-2" onClick={loadTasks} disabled={loading}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCcw className="h-3.5 w-3.5" />}
          Refresh
        </Button>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="md:col-span-2">
              <Label className="text-xs text-slate-600">Task Title</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Clarify reviewer conflict-of-interest" />
            </div>
            <div>
              <Label className="text-xs text-slate-600">Assignee</Label>
              <select
                value={assigneeUserId}
                onChange={(e) => setAssigneeUserId(e.target.value)}
                className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="">Select assignee</option>
                {staff.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.full_name || option.email || option.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs text-slate-600">Due At</Label>
              <Input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
            </div>
            <div>
              <Label className="text-xs text-slate-600">Priority</Label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as InternalTaskPriority)}
                className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                {PRIORITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <Label className="text-xs text-slate-600">Description (optional)</Label>
              <Textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add expected deliverables or notes"
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <Button className="gap-2" onClick={handleCreateTask} disabled={creating}>
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Create Task
            </Button>
          </div>
        </div>

        {loading && tasks.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-slate-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading tasks...
          </div>
        ) : orderedTasks.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 py-8 text-center text-sm text-slate-500">
            No internal tasks yet.
          </div>
        ) : (
          <div className="space-y-3">
            {orderedTasks.map((task) => {
              const canEdit = task.can_edit !== false
              const activity = activityByTask[task.id] || []
              return (
                <div key={task.id} className="rounded-lg border border-slate-200 bg-white p-3">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-semibold text-slate-900">{task.title}</p>
                        <TaskStatusBadge status={task.status} />
                        {task.is_overdue ? (
                          <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
                            Overdue
                          </span>
                        ) : null}
                      </div>
                      {task.description ? <p className="mt-1 text-sm text-slate-600">{task.description}</p> : null}
                      <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-slate-500 md:grid-cols-3">
                        <span>Assignee: {task.assignee?.full_name || task.assignee?.email || task.assignee_user_id}</span>
                        <span>Due: {formatTime(task.due_at)}</span>
                        <span>Updated: {formatTime(task.updated_at)}</span>
                      </div>
                      {!canEdit ? (
                        <p className="mt-2 text-xs text-amber-700">Only the assignee or internal editor can update this task.</p>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        aria-label={`Task ${task.title} status`}
                        value={task.status}
                        onChange={(e) => handleUpdateStatus(task, e.target.value as InternalTaskStatus)}
                        disabled={updatingTaskId === task.id || !canEdit}
                        className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm"
                      >
                        {STATUS_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <Button variant="outline" size="sm" onClick={() => toggleActivity(task.id)}>
                        {expandedTaskId === task.id ? 'Hide Activity' : 'Activity'}
                      </Button>
                    </div>
                  </div>

                  {expandedTaskId === task.id ? (
                    <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-3">
                      {loadingActivityTaskId === task.id ? (
                        <div className="text-xs text-slate-500">
                          <Loader2 className="mr-1 inline h-3.5 w-3.5 animate-spin" /> Loading activity...
                        </div>
                      ) : activity.length === 0 ? (
                        <p className="text-xs text-slate-500">No activity yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {activity.map((log) => (
                            <div key={log.id} className="rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-600">
                              <div className="font-medium text-slate-800">{log.action.replaceAll('_', ' ')}</div>
                              <div>
                                By {log.actor?.full_name || log.actor?.email || log.actor_user_id} at {formatTime(log.created_at)}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
