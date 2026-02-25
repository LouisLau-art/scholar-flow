import { ApiClient } from '@/lib/api-client'
import { FileText } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'

export const revalidate = 60

export default async function AdminManuscriptsPage() {
  /**
   * 编辑管理后台列表页 (Server Component)
   * 遵循章程：Server Components 优先，slate-900 视觉标准
   */
  const manuscripts = await ApiClient.getManuscripts()

  return (
    <div className="min-h-screen bg-muted/40">
      <SiteHeader />
      <div className="mx-auto max-w-6xl p-8">
        <header className="mb-10">
          <h1 className="font-serif text-3xl font-bold text-foreground">
            Manuscript Management
          </h1>
          <p className="text-muted-foreground">Quality control and KPI assignment.</p>
        </header>

        <div className="grid gap-6">
          {manuscripts.map((m) => (
            <div 
              key={m.id} 
              className="flex items-center justify-between rounded-lg bg-card p-6 shadow-sm ring-1 ring-border transition-shadow hover:shadow-md"
            >
              <div className="flex items-start gap-4">
                <div className="rounded-full bg-muted p-3">
                  <FileText className="h-6 w-6 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">{m.title}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-1">{m.abstract}</p>
                  <div className="mt-2 flex gap-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      m.status === 'submitted' ? 'bg-primary/15 text-primary' : 
                      m.status === 'high_similarity' ? 'bg-destructive/10 text-destructive border border-destructive/20 animate-pulse' :
                      'bg-muted text-foreground'
                    }`}>
                      {m.status.toUpperCase()}
                    </span>
                    <span className="text-xs text-muted-foreground">Created: {new Date(m.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted">
                  View PDF
                </button>
                <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
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
