import Link from 'next/link'
import { Search, ArrowRight, FileText, Settings, ShieldCheck, DollarSign } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* === 顶部导航栏 (Frontiers Style) === */}
      <header className="bg-slate-900 text-white sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/" className="font-serif text-2xl font-bold tracking-tight text-white">
                ScholarFlow
              </Link>
              <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-300">
                <Link href="#" className="hover:text-white transition-colors">Journals</Link>
                <Link href="#" className="hover:text-white transition-colors">Topics</Link>
                <Link href="/submit" className="hover:text-white transition-colors">Submit</Link>
                <Link href="/about" className="hover:text-white transition-colors">About</Link>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <button className="text-slate-300 hover:text-white">
                <Search className="h-5 w-5" />
              </button>
              <Link 
                href="/submit" 
                className="rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
              >
                Submit your manuscript
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* === Hero 区域 === */}
      <section className="bg-slate-50 py-20 lg:py-32 border-b border-slate-200">
        <div className="mx-auto max-w-7xl px-4 text-center sm:px-6 lg:px-8">
          <h1 className="font-serif text-5xl font-bold tracking-tight text-slate-900 sm:text-6xl mb-6">
            Science Open to Everyone
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-slate-600 mb-10">
            Accelerating scientific discovery through open access publishing. 
            Rigorous peer review, powered by AI and expert editors.
          </p>
          
          <div className="flex justify-center gap-4">
            <Link 
              href="/submit" 
              className="flex items-center gap-2 rounded-md bg-slate-900 px-8 py-4 text-base font-semibold text-white shadow-lg hover:bg-slate-800 transition-all"
            >
              Start Submission <ArrowRight className="h-5 w-5" />
            </Link>
            <Link 
              href="#" 
              className="flex items-center gap-2 rounded-md bg-white px-8 py-4 text-base font-semibold text-slate-900 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 transition-all"
            >
              Browse Journals
            </Link>
          </div>
        </div>
      </section>

      {/* === 核心功能入口 (模拟门户导航) === */}
      <section className="py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 font-serif">Workflow Portals</h2>
            <p className="mt-4 text-slate-500">Access specific dashboards based on your role.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* 卡片 1: 编辑后台 */}
            <Link href="/admin/manuscripts" className="group block p-8 rounded-2xl bg-white ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:ring-blue-500 transition-all">
              <div className="bg-blue-50 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-600 transition-colors">
                <Settings className="h-6 w-6 text-blue-600 group-hover:text-white" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Editorial Admin</h3>
              <p className="text-sm text-slate-500">Manage submissions, assign reviewers, and perform quality checks.</p>
            </Link>

            {/* 卡片 2: 财务后台 */}
            <Link href="/finance" className="group block p-8 rounded-2xl bg-white ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:ring-green-500 transition-all">
              <div className="bg-green-50 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-600 transition-colors">
                <DollarSign className="h-6 w-6 text-green-600 group-hover:text-white" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Finance Dashboard</h3>
              <p className="text-sm text-slate-500">Track invoices, confirm payments, and handle transactions.</p>
            </Link>

            {/* 卡片 3: 主编终审 */}
            <Link href="/admin/eic-approval" className="group block p-8 rounded-2xl bg-white ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:ring-purple-500 transition-all">
              <div className="bg-purple-50 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-600 transition-colors">
                <ShieldCheck className="h-6 w-6 text-purple-600 group-hover:text-white" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">EIC Approval</h3>
              <p className="text-sm text-slate-500">Final gatekeeping. Approve manuscripts for publication.</p>
            </Link>

            {/* 卡片 4: 投稿入口 */}
            <Link href="/submit" className="group block p-8 rounded-2xl bg-white ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:ring-slate-500 transition-all">
              <div className="bg-slate-100 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-slate-900 transition-colors">
                <FileText className="h-6 w-6 text-slate-600 group-hover:text-white" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Author Submission</h3>
              <p className="text-sm text-slate-500">Submit your research with our AI-powered fast track.</p>
            </Link>
          </div>
        </div>
      </section>

      {/* === Footer === */}
      <footer className="mt-auto bg-slate-900 py-12 text-slate-400 text-sm">
        <div className="mx-auto max-w-7xl px-4 text-center">
          <p>&copy; 2026 ScholarFlow. Open Access. Powered by Arch Linux & Next.js.</p>
        </div>
      </footer>
    </div>
  )
}