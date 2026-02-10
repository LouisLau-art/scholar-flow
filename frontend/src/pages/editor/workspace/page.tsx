import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ClipboardCheck } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'

interface Manuscript {
  id: string
  title: string
  pre_check_status: string
}

export default function AEWorkspacePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [decision, setDecision] = useState<'pass' | 'revision'>('pass')
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')

  const fetchWorkspace = async () => {
    setLoading(true)
    try {
      const data = await editorService.getAEWorkspace()
      setManuscripts(data as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkspace()
  }, [])

  const handleSubmitCheck = async (id: string) => {
    setError('')
    try {
      if (decision === 'revision' && !comment.trim()) {
        setError('Comment is required for revision.')
        return
      }
      await editorService.submitTechnicalCheck(id, { decision, comment: comment.trim() || undefined })
      setActiveId(null)
      setDecision('pass')
      setComment('')
      fetchWorkspace()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit check')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <main className="mx-auto w-[96vw] max-w-screen-2xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
              <ClipboardCheck className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Assistant Editor Workspace</h1>
              <p className="mt-1 text-slate-500 font-medium">Complete technical pre-checks and route manuscripts forward.</p>
            </div>
          </div>

          <Link href="/dashboard?tab=assistant_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full table-fixed">
            <thead className="bg-slate-50/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                <th className="w-[340px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={3} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                </tr>
              ) : manuscripts.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-10 text-center text-sm text-slate-500">No manuscripts assigned.</td>
                </tr>
              ) : (
                manuscripts.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/60">
                    <td className="px-4 py-3 text-sm text-slate-900">{m.title}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{m.pre_check_status}</td>
                    <td className="px-4 py-3">
                      {activeId === m.id ? (
                        <div className="space-y-2 min-w-[280px]">
                          <select
                            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                            value={decision}
                            onChange={(e) => setDecision(e.target.value as 'pass' | 'revision')}
                          >
                            <option value="pass">Pass to Academic</option>
                            <option value="revision">Request Revision</option>
                          </select>
                          <textarea
                            className="w-full min-h-[76px] rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            placeholder={decision === 'revision' ? 'Comment is required for revision...' : 'Optional comment...'}
                          />
                          {error ? <div className="text-xs text-rose-600">{error}</div> : null}
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSubmitCheck(m.id)}
                              className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => {
                                setActiveId(null)
                                setDecision('pass')
                                setComment('')
                                setError('')
                              }}
                              className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setActiveId(m.id)
                            setDecision('pass')
                            setComment('')
                            setError('')
                          }}
                          className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                        >
                          Submit Check
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
