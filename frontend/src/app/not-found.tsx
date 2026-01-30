import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-16 sm:px-6 lg:px-8">
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-10">
          <h1 className="font-serif text-4xl font-bold text-slate-900">404</h1>
          <p className="mt-4 text-slate-600">
            页面不存在，或该内容尚未发布。
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/"
              className="rounded-full bg-blue-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-900/20 hover:bg-blue-500 transition-colors"
            >
              返回首页
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full border border-slate-200 bg-white px-6 py-2.5 text-sm font-bold text-slate-900 hover:bg-slate-50 transition-colors"
            >
              前往 Dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

