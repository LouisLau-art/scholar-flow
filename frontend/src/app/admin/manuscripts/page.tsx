import { ApiClient } from '@/lib/api-client'
import { FileText, CheckCircle, XCircle } from 'lucide-react'

export const dynamic = 'force-dynamic'

export default async function AdminManuscriptsPage() {
  /**
   * 编辑管理后台列表页 (Server Component)
   * 遵循章程：Server Components 优先，slate-900 视觉标准
   */
  const manuscripts = await ApiClient.getManuscripts()

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-10">
          <h1 className="font-serif text-3xl font-bold text-slate-900">
            Manuscript Management
          </h1>
          <p className="text-slate-500">Quality control and KPI assignment.</p>
        </header>

        <div className="grid gap-6">
          {manuscripts.map((m) => (
            <div 
              key={m.id} 
              className="flex items-center justify-between rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start gap-4">
                <div className="rounded-full bg-slate-100 p-3">
                  <FileText className="h-6 w-6 text-slate-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{m.title}</h3>
                  <p className="text-sm text-slate-500 line-clamp-1">{m.abstract}</p>
                  <div className="mt-2 flex gap-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      m.status === 'submitted' ? 'bg-blue-100 text-blue-800' : 
                      m.status === 'high_similarity' ? 'bg-red-100 text-red-800 border border-red-200 animate-pulse' :
                      'bg-slate-100 text-slate-800'
                    }`}>
                      {m.status.toUpperCase()}
                    </span>
                    <span className="text-xs text-slate-400">Created: {new Date(m.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                  View PDF
                </button>
                <button className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  Quality Check
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
