'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { EditorApi, type ManuscriptsProcessFilters } from '@/services/editorApi'
import { Loader2, Search, RotateCcw } from 'lucide-react'

type JournalOption = { id: string; title: string; slug?: string }

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
  initial,
  onSearch,
}: {
  initial?: ManuscriptsProcessFilters
  onSearch: (filters: ManuscriptsProcessFilters) => void
}) {
  const [journals, setJournals] = useState<JournalOption[]>([])
  const [loadingJournals, setLoadingJournals] = useState(false)

  const [journalId, setJournalId] = useState(initial?.journalId || '')
  const [manuscriptId, setManuscriptId] = useState(initial?.manuscriptId || '')
  const [statuses, setStatuses] = useState<string[]>(initial?.statuses || [])

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

  const selectedStatusesText = useMemo(() => {
    if (statuses.length === 0) return 'All statuses'
    const labels = new Map(STATUS_OPTIONS.map((s) => [s.value, s.label]))
    return statuses.map((s) => labels.get(s) || s).join(', ')
  }, [statuses])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
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

        <div className="md:col-span-4">
          <Label className="text-xs text-slate-600">Manuscript ID</Label>
          <Input
            className="mt-1"
            placeholder="UUID…"
            value={manuscriptId}
            onChange={(e) => setManuscriptId(e.target.value)}
          />
        </div>

        <div className="md:col-span-4">
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
              onSearch({
                journalId: journalId || undefined,
                manuscriptId: manuscriptId.trim() || undefined,
                statuses: statuses.length ? statuses : undefined,
              })
            }
            className="gap-2"
            disabled={loadingJournals}
          >
            {loadingJournals ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setJournalId('')
              setManuscriptId('')
              setStatuses([])
              onSearch({})
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

