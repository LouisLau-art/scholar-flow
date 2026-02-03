import ArticleClient from './ArticleClient'
import { generateCitationMetadata } from '@/lib/metadata/citation'
import { Metadata } from 'next'

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_ORIGIN ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  return raw.replace(/\/$/, '')
}

// Helper to fetch article data on server
async function getArticle(id: string) {
  try {
    const origin = getBackendOrigin()
    const res = await fetch(`${origin}/api/v1/manuscripts/articles/${encodeURIComponent(id)}`, { cache: 'no-store' })
    if (!res.ok) return null
    const json = await res.json()
    return json.success ? json.data : null
  } catch (error) {
    console.error("Error fetching article for metadata:", error)
    return null
  }
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const article = await getArticle(params.id)
  
  if (!article) {
    return {
      title: 'Article Not Found',
    }
  }

  // Convert article data to format expected by generateCitationMetadata
  // The API response structure needs to match what citation.ts expects
  const metaArticle = {
    title: article.title,
    authors: article.authors?.map((a: any) => ({
      firstName: a.first_name,
      lastName: a.last_name,
      affiliation: a.affiliation
    })) || [],
    publicationDate: article.published_at ? new Date(article.published_at).toISOString().split('T')[0] : '',
    journalTitle: article.journals?.title || 'Scholar Flow Journal',
    doi: article.doi || '',
    // 中文注释: MVP 阶段不在 metadata 里承诺稳定可长期访问的 PDF URL（Storage 通常为私有 + signed url）。
    // 若未来要支持 Google Scholar 更好抓取，可增加一个稳定的公开 PDF 入口（例如 /api/v1/manuscripts/articles/{id}/pdf）。
    pdfUrl: undefined,
    abstract: article.abstract,
  }

  const tags = generateCitationMetadata(metaArticle)
  
  // Convert tags to Next.js metadata format
  // 'other' allows custom meta tags
  const other: Record<string, string | string[]> = {}
  tags.forEach(tag => {
    const existing = other[tag.name]
    if (existing) {
        if (Array.isArray(existing)) {
            existing.push(tag.content)
        } else {
            other[tag.name] = [existing, tag.content]
        }
    } else {
        other[tag.name] = tag.content
    }
  })

  return {
    title: article.title,
    description: article.abstract,
    other: other,
  }
}

export default async function ArticlePage({ params }: { params: { id: string } }) {
  const article = await getArticle(params.id)
  return <ArticleClient initialArticle={article} />
}
