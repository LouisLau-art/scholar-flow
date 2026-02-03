import SubmissionForm from '@/components/SubmissionForm'
import SiteHeader from '@/components/layout/SiteHeader'

export default function SubmitPage() {
  /**
   * 投稿页面框架 (Server Component)
   * 遵循章程：大标题衬线体，配色锁定为 slate-900，原子化设计
   */
  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <div className="mx-auto max-w-4xl p-8">
        <header className="mb-12 border-b border-slate-200 pb-6">
          <h1 className="font-serif text-4xl font-bold text-slate-900">
            Submit Your Manuscript
          </h1>
          <p className="mt-2 text-slate-600">
            Frontiers-inspired academic submission workflow.
          </p>
        </header>

        <main className="rounded-lg bg-white p-8 shadow-sm ring-1 ring-slate-200">
          <SubmissionForm />
        </main>
      </div>
    </div>
  )
}
