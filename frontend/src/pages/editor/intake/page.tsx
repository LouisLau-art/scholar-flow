import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Inbox } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'
import { AssignAEModal } from '@/components/AssignAEModal'
import { getAssistantEditors } from '@/services/assistantEditorsCache'

// Mock types
interface Manuscript {
  id: string
  title: string
  pre_check_status: string
}

export default function MEIntakePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | null>(null)

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const data = await editorService.getIntakeQueue()
      // Cast for mock compatibility since service returns any[]/mock
      setManuscripts(data as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
    // 中文注释：预取 AE 列表，避免首次点击 Assign AE 时才触发网络请求导致卡顿
    void getAssistantEditors().catch(() => {})
  }, [])

  const openAssignModal = (id: string) => {
    setSelectedManuscriptId(id)
    setAssignModalOpen(true)
  }

  return (
    <QueryProvider>
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <main className="mx-auto w-[96vw] max-w-screen-2xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
                <Inbox className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Managing Editor Intake Queue</h1>
                <p className="mt-1 text-slate-500 font-medium">Assign manuscripts to assistant editors for technical checks.</p>
              </div>
            </div>

            <Link href="/dashboard?tab=managing_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
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
                  <th className="w-32 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                  </tr>
                ) : manuscripts.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-10 text-center text-sm text-slate-500">No manuscripts in intake.</td>
                  </tr>
                ) : (
                  manuscripts.map((m) => (
                    <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/60">
                      <td className="px-4 py-3 text-sm text-slate-900">{m.title}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{m.pre_check_status}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => openAssignModal(m.id)}
                          className="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100"
                        >
                          Assign AE
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {selectedManuscriptId && (
            <AssignAEModal
              isOpen={assignModalOpen}
              onClose={() => setAssignModalOpen(false)}
              manuscriptId={selectedManuscriptId}
              onAssignSuccess={fetchQueue}
            />
          )}
        </main>
      </div>
    </QueryProvider>
  )
}
