'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { EditorApi } from '@/services/editorApi'
import { ChevronDown, Loader2, Search, RotateCcw } from 'lucide-react'
import type { EditorRbacContext } from '@/types/rbac'

type JournalOption = { id: string; title: string; slug?: string }
type StaffOption = { id: string; email?: string; full_name?: string }
const FILTER_META_CACHE_TTL_MS = 300_000

let journalsCache: { data: JournalOption[]; cachedAt: number } | null = null
let staffCache: { data: StaffOption[]; cachedAt: number } | null = null

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
  rbacContext,
}: {
  className?: string
  rbacContext?: EditorRbacContext | null
}) {
  const router = useRouter()
  const pathname = usePathname() ?? '/editor/process'
  const searchParams = useSearchParams()
  const searchKey = searchParams?.toString() || ''

  const [journals, setJournals] = useState<JournalOption[]>([])
  const [loadingJournals, setLoadingJournals] = useState(false)

  const [staff, setStaff] = useState<StaffOption[]>([])
  const [loadingStaff, setLoadingStaff] = useState(false)

  const applied = useMemo(() => {
    const parsed = new URLSearchParams(searchKey)
    const q = (parsed.get('q') || '').trim()
    const journalId = parsed.get('journal_id') || ''
    const editorId = parsed.get('editor_id') || ''
    const overdueOnly = ['1', 'true', 'yes', 'on'].includes((parsed.get('overdue_only') || '').toLowerCase())
    const rawStatuses = parsed.getAll('status')
    const statuses =
      rawStatuses.length === 1 && rawStatuses[0]?.includes(',')
        ? rawStatuses[0].split(',').map((s) => s.trim()).filter(Boolean)
        : rawStatuses
    return { q, journalId, editorId, statuses, overdueOnly }
  }, [searchKey])

  const [q, setQ] = useState(applied.q)
  const [journalId, setJournalId] = useState(applied.journalId)
  const [editorId, setEditorId] = useState(applied.editorId)
  const [statuses, setStatuses] = useState<string[]>(applied.statuses)
  const [overdueOnly, setOverdueOnly] = useState<boolean>(applied.overdueOnly)
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false)

  const normalizedRoles = useMemo(() => {
    const rows = rbacContext?.normalized_roles || []
    return new Set(rows.map((item) => String(item).toLowerCase()))
  }, [rbacContext])
  const canFilterByJournal = useMemo(
    () =>
      normalizedRoles.has('admin') ||
      normalizedRoles.has('managing_editor') ||
      normalizedRoles.has('editor_in_chief'),
    [normalizedRoles]
  )
  const canFilterByEditor = canFilterByJournal

  const qDebounceTimer = useRef<number | null>(null)
  const mountedRef = useRef(false)
  const statusDropdownRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let alive = true
    const now = Date.now()
    const cacheValid = Boolean(journalsCache && now - journalsCache.cachedAt < FILTER_META_CACHE_TTL_MS)
    if (cacheValid && journalsCache) {
      setJournals(journalsCache.data)
      setLoadingJournals(false)
    }

    async function load() {
      try {
        if (!cacheValid) setLoadingJournals(true)
        const res = await EditorApi.listJournals()
        if (!alive) return
        if (res?.success) {
          const nextRows = res.data || []
          journalsCache = { data: nextRows, cachedAt: Date.now() }
          setJournals(nextRows)
        }
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
    const now = Date.now()
    const cacheValid = Boolean(staffCache && now - staffCache.cachedAt < FILTER_META_CACHE_TTL_MS)
    if (cacheValid && staffCache) {
      setStaff(staffCache.data)
      setLoadingStaff(false)
    }

    async function loadStaff() {
      try {
        if (!cacheValid) setLoadingStaff(true)
        const res = await EditorApi.listInternalStaff('')
        if (!alive) return
        if (res?.success) {
          const nextRows = res.data || []
          staffCache = { data: nextRows, cachedAt: Date.now() }
          setStaff(nextRows)
        }
      } finally {
        if (alive) setLoadingStaff(false)
      }
    }
    loadStaff()
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (!statusDropdownRef.current) return
      if (!statusDropdownRef.current.contains(event.target as Node)) {
        setStatusDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
    }
  }, [])

  useEffect(() => {
    if (!canFilterByJournal && journalId) setJournalId('')
  }, [canFilterByJournal, journalId])

  useEffect(() => {
    if (!canFilterByEditor && editorId) setEditorId('')
  }, [canFilterByEditor, editorId])

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
    setOverdueOnly(applied.overdueOnly)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applied.q, applied.journalId, applied.editorId, applied.statuses.join('|'), applied.overdueOnly])

  function updateUrl(partial: {
    q?: string | null
    journalId?: string | null
    editorId?: string | null
    statuses?: string[] | null
    overdueOnly?: boolean | null
  }) {
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
    if ('overdueOnly' in partial) {
      if (partial.overdueOnly) next.set('overdue_only', 'true')
      else next.delete('overdue_only')
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

  function toggleStatus(statusValue: string) {
    setStatuses((prev) => {
      if (prev.includes(statusValue)) {
        return prev.filter((s) => s !== statusValue)
      }
      return [...prev, statusValue]
    })
  }

  return (
    <div className={className ? className : 'rounded-xl border border-border bg-card p-4'}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
          <Label className="text-xs text-muted-foreground">Search (Title / UUID)</Label>
          <Input className="mt-1" placeholder="Energy, 9286... (UUID) ..." value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        {canFilterByJournal ? (
          <div className="md:col-span-3">
            <Label className="text-xs text-muted-foreground">Journal</Label>
            <div className="mt-1">
              <Select value={journalId || '__all'} onValueChange={(value) => setJournalId(value === '__all' ? '' : value)}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder={loadingJournals ? 'Loading…' : 'All journals'} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">{loadingJournals ? 'Loading…' : 'All journals'}</SelectItem>
                  {journals.map((j) => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : null}

        {canFilterByEditor ? (
          <div className="md:col-span-3">
            <Label className="text-xs text-muted-foreground">Assign Editor</Label>
            <div className="mt-1">
              <Select value={editorId || '__all'} onValueChange={(value) => setEditorId(value === '__all' ? '' : value)}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder={loadingStaff ? 'Loading…' : 'All editors'} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">{loadingStaff ? 'Loading…' : 'All editors'}</SelectItem>
                  {staff.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.full_name || s.email || s.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : null}

        <div className="md:col-span-2">
          <Label className="text-xs text-muted-foreground">Status</Label>
          <div className="relative mt-1" ref={statusDropdownRef}>
            <button
              type="button"
              onClick={() => setStatusDropdownOpen((v) => !v)}
              className="h-10 w-full rounded-md border border-border bg-card px-3 text-left text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              aria-haspopup="listbox"
              aria-expanded={statusDropdownOpen}
            >
              <span className="block truncate pr-7">{selectedStatusesText}</span>
              <ChevronDown className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </button>

            {statusDropdownOpen ? (
              <div className="absolute z-40 mt-2 w-full min-w-[230px] rounded-md border border-border bg-card shadow-lg">
                <div className="max-h-56 overflow-auto p-2">
                  {STATUS_OPTIONS.map((s) => (
                    <label key={s.value} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-foreground hover:bg-muted/50">
                      <input
                        type="checkbox"
                        checked={statuses.includes(s.value)}
                        onChange={() => toggleStatus(s.value)}
                        className="h-4 w-4 rounded border-border"
                      />
                      <span>{s.label}</span>
                    </label>
                  ))}
                </div>
                <div className="flex items-center justify-between border-t border-border px-2 py-2">
                  <button
                    type="button"
                    onClick={() => setStatuses([])}
                    className="rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatusDropdownOpen(false)}
                    className="rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="md:col-span-12 flex flex-wrap gap-2 pt-2">
          <label className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="h-4 w-4"
            />
            Overdue only
          </label>
          <Button
            onClick={() => {
              setStatusDropdownOpen(false)
              updateUrl({
                q,
                journalId: canFilterByJournal ? journalId || null : null,
                editorId: canFilterByEditor ? editorId || null : null,
                statuses: statuses.length ? statuses : null,
                overdueOnly,
              })
            }}
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
              setOverdueOnly(false)
              setStatusDropdownOpen(false)
              updateUrl({ q: null, journalId: null, editorId: null, statuses: null, overdueOnly: null })
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
