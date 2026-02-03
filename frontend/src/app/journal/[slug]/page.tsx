import { notFound } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'

export const revalidate = 60

type PageData = {
  slug: string
  title: string
  content?: string | null
}

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_ORIGIN ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  return raw.replace(/\/$/, '')
}

async function fetchCmsPage(slug: string): Promise<PageData> {
  try {
    const origin = getBackendOrigin()
    const res = await fetch(`${origin}/api/v1/cms/pages/${encodeURIComponent(slug)}`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) {
      notFound()
    }
    const body = await res.json()
    if (!body?.success || !body?.data) {
      notFound()
    }
    return body.data as PageData
  } catch (error) {
    console.error('Failed to load CMS page:', error)
    notFound()
  }
}

export default async function JournalCmsPage({ params }: { params: { slug: string } }) {
  const page = await fetchCmsPage(params.slug)

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <article className="bg-white rounded-3xl shadow-sm border border-slate-100 p-8">
          <h1 className="font-serif text-4xl font-bold text-slate-900">{page.title}</h1>
          {/* 中文注释：MVP 阶段 CMS 内容默认由内部人员维护，不把用户生成内容写入 CMS；因此不在服务端引入 DOMPurify/jsdom，避免 Vercel Node 运行时 ESM/CJS 兼容问题。 */}
          <div className="mt-8 prose max-w-none text-slate-800" dangerouslySetInnerHTML={{ __html: page.content || '' }} />
        </article>
      </main>
    </div>
  )
}
