import ArticleClient from './ArticleClient'
import { generateCitationMetadata } from '@/lib/metadata/citation'
import { Metadata } from 'next'
import { cache } from 'react'

export const revalidate = 60

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_ORIGIN ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  return raw.replace(/\/$/, '')
}

// Helper to fetch article data on server
const getArticle = cache(async (id: string) => {
  try {
    const origin = getBackendOrigin()
    const res = await fetch(
      `${origin}/api/v1/manuscripts/articles/${encodeURIComponent(id)}`,
      {
        next: {
          revalidate,
          tags: ['articles', `article:${id}`],
        },
      }
    )
    if (!res.ok) return null
    const json = await res.json()
    return json.success ? json.data : null
  } catch (error) {
    console.error("Error fetching article for metadata:", error)
    return null
  }
})

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const article = await getArticle(params.id)
  
  if (!article) {
    return {
      title: 'Article Not Found',
    }
  }

  // Convert article data to format expected by generateCitationMetadata
  // The API response structure needs to match what citation.ts expects
  const origin = getBackendOrigin()
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
    // 中文注释: 公开的 /pdf 入口会 302 到短期 signed URL，可用于 Scholar 抓取 citation_pdf_url。
    pdfUrl: `${origin}/api/v1/manuscripts/articles/${encodeURIComponent(params.id)}/pdf`,
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
