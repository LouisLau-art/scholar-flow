import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-16 sm:px-6 lg:px-8">
        <div className="bg-card rounded-3xl shadow-sm border border-border/60 p-10">
          <h1 className="font-serif text-4xl font-bold text-foreground">404</h1>
          <p className="mt-4 text-muted-foreground">
            页面不存在，或该内容尚未发布。
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/"
              className="rounded-full bg-primary px-6 py-2.5 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary/90 transition-colors"
            >
              返回首页
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full border border-border bg-background px-6 py-2.5 text-sm font-bold text-foreground hover:bg-muted transition-colors"
            >
              前往 Dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
