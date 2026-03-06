import { fetchBackendJson } from '@/lib/server-backend-fetch'

export type PublicJournal = {
  id: string
  title: string
  slug: string
  description?: string | null
  issn?: string | null
  impact_factor?: number | string | null
  cover_url?: string | null
}

export type PublicJournalArticle = {
  id: string
  title?: string | null
  abstract?: string | null
  doi?: string | null
  published_at?: string | null
  created_at?: string | null
}

export type PublicJournalDetail = {
  journal: PublicJournal
  articles: PublicJournalArticle[]
}

const JOURNALS_REVALIDATE_SECONDS = 300

function parseImpact(value: number | string | null | undefined): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}

export function getJournalImpactLabel(value: number | string | null | undefined): string {
  const parsed = parseImpact(value)
  return parsed == null ? 'N/A' : parsed.toFixed(2)
}

export async function getPublicJournals(): Promise<PublicJournal[]> {
  const result = await fetchBackendJson<{ success?: boolean; data?: PublicJournal[] }>(
    '/api/v1/public/journals',
    {
      label: 'public-journals',
      next: {
        revalidate: JOURNALS_REVALIDATE_SECONDS,
        tags: ['public-journals'],
      },
    }
  )
  if (!result.ok || !result.data?.success || !Array.isArray(result.data?.data)) return []
  return result.data.data
}

export async function getPublicJournalDetail(slug: string): Promise<PublicJournalDetail | null> {
  if (!slug.trim()) return null

  const result = await fetchBackendJson<{
    success?: boolean
    journal?: PublicJournal
    articles?: PublicJournalArticle[]
  }>(`/api/v1/manuscripts/journals/${encodeURIComponent(slug)}`, {
    label: `public-journal-detail:${slug}`,
    next: {
      revalidate: JOURNALS_REVALIDATE_SECONDS,
      tags: ['public-journals', `public-journal:${slug.toLowerCase()}`],
    },
  })
  if (result.status === 404 || !result.ok) return null
  if (!result.data?.success || !result.data?.journal) return null

  const articles = Array.isArray(result.data?.articles) ? result.data.articles : []
  const sortedArticles = [...articles].sort((a, b) => {
    const aTs = new Date(a.published_at || a.created_at || 0).getTime()
    const bTs = new Date(b.published_at || b.created_at || 0).getTime()
    return bTs - aTs
  })

  return {
    journal: result.data.journal,
    articles: sortedArticles,
  }
}
