import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowRight, BookOpenText, CalendarDays, FileText, Landmark } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDateLocal } from '@/lib/date-display'
import { getJournalImpactLabel, getPublicJournalDetail, type PublicJournalArticle } from '@/services/public-journals'

export const revalidate = 300

type JournalDetailPageProps = {
  params: {
    slug: string
  }
}

function buildJournalDescription(raw?: string | null): string {
  const value = String(raw || '').trim()
  if (value) return value
  return 'This journal publishes peer-reviewed research through the ScholarFlow workflow platform.'
}

function articleTimeLabel(article: PublicJournalArticle): string {
  return formatDateLocal(article.published_at || article.created_at || null)
}

export async function generateMetadata({ params }: JournalDetailPageProps): Promise<Metadata> {
  const detail = await getPublicJournalDetail(params.slug)
  if (!detail) {
    return {
      title: 'Journal not found',
      description: 'The requested journal could not be found.',
    }
  }

  const description = buildJournalDescription(detail.journal.description)
  const impactLabel = getJournalImpactLabel(detail.journal.impact_factor)

  return {
    title: `${detail.journal.title} | Journals`,
    description,
    openGraph: {
      title: detail.journal.title,
      description,
      type: 'website',
    },
    alternates: {
      canonical: `/journals/${detail.journal.slug}`,
    },
    keywords: [
      detail.journal.title,
      'journal',
      'scholarflow',
      `impact ${impactLabel}`,
    ],
  }
}

export default async function JournalDetailPage({ params }: JournalDetailPageProps) {
  const detail = await getPublicJournalDetail(params.slug)
  if (!detail) {
    notFound()
  }

  const { journal, articles } = detail
  const description = buildJournalDescription(journal.description)
  const impactLabel = getJournalImpactLabel(journal.impact_factor)

  return (
    <div className="min-h-screen bg-muted/40 text-foreground">
      <SiteHeader />

      <main className="mx-auto max-w-7xl px-4 pb-16 pt-12 sm:px-6 lg:px-8">
        <section className="rounded-3xl border border-border bg-card p-8 shadow-xl sm:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.35fr_0.95fr]">
            <div className="space-y-5">
              <Badge variant="secondary" className="w-fit gap-1.5 text-xs uppercase tracking-wider">
                <Landmark className="h-3.5 w-3.5" />
                Journal Profile
              </Badge>
              <h1 className="font-serif text-4xl font-semibold leading-tight text-foreground sm:text-5xl">
                {journal.title}
              </h1>
              <p className="max-w-3xl text-base leading-relaxed text-muted-foreground">{description}</p>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button asChild>
                  <Link href="/submit">Submit Manuscript</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href={`/search?mode=journals&q=${encodeURIComponent(journal.title)}`}>Search Similar Journals</Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-3 rounded-2xl border border-border/80 bg-background/80 p-4">
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">ISSN</div>
                <div className="mt-1 text-lg font-semibold">{journal.issn || 'Pending'}</div>
              </div>
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Impact Factor</div>
                <div className="mt-1 text-lg font-semibold">{impactLabel}</div>
              </div>
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Slug</div>
                <div className="mt-1 truncate font-mono text-sm text-muted-foreground">{journal.slug}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-border bg-card p-6">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="inline-flex items-center gap-2 text-2xl font-semibold text-foreground">
              <FileText className="h-6 w-6 text-primary" />
              Latest Published Articles
            </h2>
            <Badge variant="outline">{articles.length} article(s)</Badge>
          </div>

          {articles.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-muted/40 p-8 text-center text-sm text-muted-foreground">
              No published articles in this journal yet.
            </div>
          ) : (
            <div className="grid gap-4">
              {articles.map((article) => (
                <Link
                  key={article.id}
                  href={`/articles/${article.id}`}
                  className="group rounded-xl border border-border bg-card p-5 transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
                >
                  <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-wider text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {articleTimeLabel(article)}
                    </span>
                    <span className="hidden h-1 w-1 rounded-full bg-border sm:inline-block" />
                    <span className="truncate">DOI: {article.doi || 'Pending'}</span>
                  </div>

                  <h3 className="mt-3 text-xl font-semibold leading-snug text-foreground transition-colors group-hover:text-primary">
                    {article.title || 'Untitled article'}
                  </h3>
                  <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                    {article.abstract || 'Open the article page to view full details.'}
                  </p>

                  <div className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary">
                    Read article
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="mt-8 rounded-2xl border border-border bg-card p-6">
          <h2 className="inline-flex items-center gap-2 text-xl font-semibold text-foreground">
            <BookOpenText className="h-5 w-5 text-primary" />
            About This Journal
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{description}</p>
        </section>
      </main>
    </div>
  )
}
