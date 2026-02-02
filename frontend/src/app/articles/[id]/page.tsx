import ArticleClient from './ArticleClient'
import { generateCitationMetadata } from '@/lib/metadata/citation'
import { Metadata } from 'next'

// Helper to fetch article data on server
async function getArticle(id: string) {
  try {
    // Assuming backend is reachable at 127.0.0.1:8000 from the nextjs server container/process
    const res = await fetch(`http://127.0.0.1:8000/api/v1/manuscripts/articles/${id}`, { cache: 'no-store' })
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
    pdfUrl: article.file_path ? `https://scholarflow.com/api/v1/manuscripts/${article.id}/pdf` : undefined, // Placeholder URL
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
