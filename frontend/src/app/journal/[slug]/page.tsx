import { notFound } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { fetchBackendJson } from '@/lib/server-backend-fetch'

export const revalidate = 60

type PageData = {
  slug: string
  title: string
  content?: string | null
}

async function fetchCmsPage(slug: string): Promise<PageData> {
  const result = await fetchBackendJson<{ success?: boolean; data?: PageData }>(
    `/api/v1/cms/pages/${encodeURIComponent(slug)}`,
    {
      label: `cms-page:${slug}`,
      next: { revalidate: 60 },
    }
  )
  if (!result.ok || !result.data?.success || !result.data?.data) {
    notFound()
  }

  return result.data.data
}

export default async function JournalCmsPage({ params }: { params: { slug: string } }) {
  const page = await fetchCmsPage(params.slug)

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <article className="bg-card rounded-3xl shadow-sm border border-border/60 p-8">
          <h1 className="font-serif text-4xl font-bold text-foreground">{page.title}</h1>
          {/* 中文注释：MVP 阶段 CMS 内容默认由内部人员维护，不把用户生成内容写入 CMS；因此不在服务端引入 DOMPurify/jsdom，避免 Vercel Node 运行时 ESM/CJS 兼容问题。 */}
          <div className="mt-8 prose max-w-none text-foreground" dangerouslySetInnerHTML={{ __html: page.content || '' }} />
        </article>
      </main>
    </div>
  )
}
