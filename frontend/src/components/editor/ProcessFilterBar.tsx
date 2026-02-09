'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { EditorApi } from '@/services/editorApi'
import { Loader2, Search, RotateCcw } from 'lucide-react'

type JournalOption = { id: string; title: string; slug?: string }
type StaffOption = { id: string; email?: string; full_name?: string }

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'pre_check', label: 'Pre-check' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'major_revision', label: 'Major Revision' },
  { value: 'minor_revision', label: 'Minor Revision' },
  { value: 'resubmitted', label: 'Resubmitted' },
  { value: 'decision', label: 'Decision' },
  { value: 'decision_done', label: 'Decision Done' },
  { value: 'approved', label: 'Accepted' },
  { value: 'layout', label: 'Layout' },
  { value: 'english_editing', label: 'English Editing' },
  { value: 'proofreading', label: 'Proofreading' },
  { value: 'published', label: 'Published' },
  { value: 'rejected', label: 'Rejected' },
]

export function ProcessFilterBar({
  className,
}: {
  className?: string
}) {
  const router = useRouter()
  const pathname = usePathname() ?? '/editor/process'
  const searchParams = useSearchParams()

  const [journals, setJournals] = useState<JournalOption[]>([])
  const [loadingJournals, setLoadingJournals] = useState(false)

  const [staff, setStaff] = useState<StaffOption[]>([])
  const [loadingStaff, setLoadingStaff] = useState(false)

  const applied = useMemo(() => {
    const q = (searchParams?.get('q') || '').trim()
    const journalId = searchParams?.get('journal_id') || ''
    const editorId = searchParams?.get('editor_id') || ''
    const rawStatuses = searchParams?.getAll('status') || []
    const statuses =
      rawStatuses.length === 1 && rawStatuses[0]?.includes(',')
        ? rawStatuses[0].split(',').map((s) => s.trim()).filter(Boolean)
        : rawStatuses
    return { q, journalId, editorId, statuses }
  }, [searchParams])

  const [q, setQ] = useState(applied.q)
  const [journalId, setJournalId] = useState(applied.journalId)
  const [editorId, setEditorId] = useState(applied.editorId)
  const [statuses, setStatuses] = useState<string[]>(applied.statuses)

  const qDebounceTimer = useRef<number | null>(null)
  const mountedRef = useRef(false)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        setLoadingJournals(true)
        const res = await EditorApi.listJournals()
        if (!alive) return
        if (res?.success) setJournals(res.data || [])
      } finally {
        if (alive) setLoadingJournals(false)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    let alive = true
    async function loadStaff() {
      try {
        setLoadingStaff(true)
        const res = await EditorApi.listInternalStaff('')
        if (!alive) return
        if (res?.success) setStaff(res.data || [])
      } finally {
        if (alive) setLoadingStaff(false)
      }
    }
    loadStaff()
    return () => {
      alive = false
    }
  }, [])

  // URL -> Draft 同步（支持浏览器前进/后退）
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true
      return
    }
    setQ(applied.q)
    setJournalId(applied.journalId)
    setEditorId(applied.editorId)
    setStatuses(applied.statuses)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applied.q, applied.journalId, applied.editorId, applied.statuses.join('|')])

  function updateUrl(partial: { q?: string | null; journalId?: string | null; editorId?: string | null; statuses?: string[] | null }) {
    const next = new URLSearchParams(searchParams?.toString() || '')

    if ('q' in partial) {
      const v = (partial.q || '').trim()
      if (v) next.set('q', v)
      else next.delete('q')
    }
    if ('journalId' in partial) {
      const v = (partial.journalId || '').trim()
      if (v) next.set('journal_id', v)
      else next.delete('journal_id')
    }
    if ('editorId' in partial) {
      const v = (partial.editorId || '').trim()
      if (v) next.set('editor_id', v)
      else next.delete('editor_id')
    }
    if ('statuses' in partial) {
      next.delete('status')
      for (const s of partial.statuses || []) next.append('status', s)
    }

    const qs = next.toString()
    router.push(qs ? `${pathname}?${qs}` : pathname)
  }

  // T012: 文本搜索 debounce（仅自动同步 q，避免未点击 Search 时触发其他过滤器落地）
  useEffect(() => {
    if (qDebounceTimer.current) window.clearTimeout(qDebounceTimer.current)
    qDebounceTimer.current = window.setTimeout(() => {
      if ((q || '').trim() === applied.q) return
      updateUrl({ q })
    }, 350)
    return () => {
      if (qDebounceTimer.current) window.clearTimeout(qDebounceTimer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  const selectedStatusesText = useMemo(() => {
    if (statuses.length === 0) return 'All statuses'
    const labels = new Map(STATUS_OPTIONS.map((s) => [s.value, s.label]))
    return statuses.map((s) => labels.get(s) || s).join(', ')
  }, [statuses])

  return (
    <div className={className ? className : 'rounded-xl border border-slate-200 bg-white p-4'}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
          <Label className="text-xs text-slate-600">Search (Title / UUID)</Label>
          <Input className="mt-1" placeholder="Energy, 9286... (UUID) ..." value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        <div className="md:col-span-3">
          <Label className="text-xs text-slate-600">Journal</Label>
          <div className="mt-1">
            <select
              value={journalId}
              onChange={(e) => setJournalId(e.target.value)}
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900/10"
            >
              <option value="">{loadingJournals ? 'Loading…' : 'All journals'}</option>
              {journals.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="md:col-span-3">
          <Label className="text-xs text-slate-600">Assign Editor</Label>
          <div className="mt-1">
            <select
              value={editorId}
              onChange={(e) => setEditorId(e.target.value)}
              className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900/10"
            >
              <option value="">{loadingStaff ? 'Loading…' : 'All editors'}</option>
              {staff.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name || s.email || s.id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="md:col-span-2">
          <Label className="text-xs text-slate-600">Status (multi-select)</Label>
          <select
            multiple
            value={statuses}
            onChange={(e) => {
              const next: string[] = []
              for (const opt of Array.from(e.target.selectedOptions)) next.push(opt.value)
              setStatuses(next)
            }}
            className="mt-1 h-24 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-900/10"
            aria-label="Statuses"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-400">{selectedStatusesText}</p>
        </div>

        <div className="md:col-span-12 flex flex-wrap gap-2 pt-2">
          <Button
            onClick={() =>
              updateUrl({
                q,
                journalId: journalId || null,
                editorId: editorId || null,
                statuses: statuses.length ? statuses : null,
              })
            }
            className="gap-2"
            disabled={loadingJournals || loadingStaff}
          >
            {loadingJournals || loadingStaff ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Search
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setQ('')
              setJournalId('')
              setEditorId('')
              setStatuses([])
              updateUrl({ q: null, journalId: null, editorId: null, statuses: null })
            }}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </div>
      </div>
    </div>
  )
}
