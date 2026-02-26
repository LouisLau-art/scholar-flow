import { getBackendOrigin } from '@/lib/backend-origin'

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
  try {
    const origin = getBackendOrigin()
    const res = await fetch(`${origin}/api/v1/public/journals`, {
      next: {
        revalidate: JOURNALS_REVALIDATE_SECONDS,
        tags: ['public-journals'],
      },
    })
    if (!res.ok) return []
    const payload = await res.json().catch(() => null)
    if (!payload?.success || !Array.isArray(payload?.data)) return []
    return payload.data as PublicJournal[]
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('Failed to load public journals:', error)
    }
    return []
  }
}

export async function getPublicJournalDetail(slug: string): Promise<PublicJournalDetail | null> {
  if (!slug.trim()) return null

  try {
    const origin = getBackendOrigin()
    const res = await fetch(`${origin}/api/v1/manuscripts/journals/${encodeURIComponent(slug)}`, {
      next: {
        revalidate: JOURNALS_REVALIDATE_SECONDS,
        tags: ['public-journals', `public-journal:${slug.toLowerCase()}`],
      },
    })
    if (res.status === 404 || !res.ok) return null

    const payload = await res.json().catch(() => null)
    if (!payload?.success || !payload?.journal) return null

    const articles = Array.isArray(payload?.articles) ? (payload.articles as PublicJournalArticle[]) : []
    const sortedArticles = [...articles].sort((a, b) => {
      const aTs = new Date(a.published_at || a.created_at || 0).getTime()
      const bTs = new Date(b.published_at || b.created_at || 0).getTime()
      return bTs - aTs
    })

    return {
      journal: payload.journal as PublicJournal,
      articles: sortedArticles,
    }
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('Failed to load public journal detail:', error)
    }
    return null
  }
}
