import DOMPurify from 'isomorphic-dompurify'
import { headers } from 'next/headers'
import { notFound } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import CmsPageClient from './CmsPageClient'

export const revalidate = 60

type PageData = {
  slug: string
  title: string
  content?: string | null
}

function getBaseUrlFromHeaders(): string {
  const h = headers()
  const host = h.get('x-forwarded-host') ?? h.get('host')
  const proto = h.get('x-forwarded-proto') ?? 'http'
  if (!host) return 'http://localhost:3000'
  return `${proto}://${host}`
}

async function fetchCmsPage(slug: string): Promise<PageData> {
  const baseUrl = getBaseUrlFromHeaders()
  const res = await fetch(`${baseUrl}/api/v1/cms/pages/${encodeURIComponent(slug)}`, { next: { revalidate: 60 } })
  if (res.status === 404) return null as unknown as PageData
  if (!res.ok) {
    throw new Error(`CMS fetch failed: ${res.status}`)
  }
  const body = await res.json()
  if (!body?.success || !body?.data) {
    throw new Error('CMS response invalid')
  }
  return body.data as PageData
}

export default async function JournalCmsPage({ params }: { params: { slug: string } }) {
  try {
    const page = await fetchCmsPage(params.slug)
    if (!page) {
      notFound()
    }
    const html = DOMPurify.sanitize(page.content || '', { USE_PROFILES: { html: true } })

    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <SiteHeader />

        <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
          <article className="bg-white rounded-3xl shadow-sm border border-slate-100 p-8">
            <h1 className="font-serif text-4xl font-bold text-slate-900">{page.title}</h1>
            <div className="mt-8 prose max-w-none text-slate-800" dangerouslySetInnerHTML={{ __html: html }} />
          </article>
        </main>
      </div>
    )
  } catch {
    // 中文注释:
    // - SSR 拉取 CMS 数据失败时（例如：本地未启动后端），降级为 Client Fetch。
    // - 这使得 Playwright 可通过 `page.route('**/api/v1/cms/pages/:slug')` 进行端到端回归。
    return <CmsPageClient slug={params.slug} />
  }
}
