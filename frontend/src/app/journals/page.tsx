import type { Metadata } from 'next'
import Link from 'next/link'
import { BookOpen, Search, ArrowRight, Sparkles } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { demoJournals } from '@/lib/demo-journals'
import { getJournalImpactLabel, getPublicJournals, type PublicJournal } from '@/services/public-journals'

export const revalidate = 300

export const metadata: Metadata = {
  title: 'Journals',
  description: 'Explore all journals published on ScholarFlow, including scope, ISSN, and impact indicators.',
  openGraph: {
    title: 'ScholarFlow Journals',
    description: 'Discover journals across disciplines and browse their latest published research.',
    type: 'website',
  },
}

type JournalsPageProps = {
  searchParams?: {
    q?: string | string[]
  }
}

function pickFirst(value?: string | string[]): string {
  if (Array.isArray(value)) return value[0] || ''
  return value || ''
}

function getFilteredJournals(journals: PublicJournal[], query: string): PublicJournal[] {
  if (!query) return journals
  const keyword = query.toLowerCase()
  return journals.filter((journal) => {
    const title = String(journal.title || '').toLowerCase()
    const description = String(journal.description || '').toLowerCase()
    const issn = String(journal.issn || '').toLowerCase()
    return title.includes(keyword) || description.includes(keyword) || issn.includes(keyword)
  })
}

function getJournalStats(journals: PublicJournal[]) {
  const withImpact = journals
    .map((journal) => Number(journal.impact_factor))
    .filter((value) => Number.isFinite(value))
  const avgImpact =
    withImpact.length > 0
      ? (withImpact.reduce((sum, value) => sum + value, 0) / withImpact.length).toFixed(2)
      : 'N/A'

  return {
    total: journals.length,
    withImpact: withImpact.length,
    avgImpact,
  }
}

function asFallbackJournals(): PublicJournal[] {
  return demoJournals.map((item) => ({
    id: item.id,
    title: item.title,
    slug: item.slug,
    description: item.description || `${item.category} journal on ScholarFlow.`,
    issn: item.issn || null,
    impact_factor: Number(item.impact),
  }))
}

export default async function JournalsPage({ searchParams }: JournalsPageProps) {
  const query = pickFirst(searchParams?.q).trim()
  const remoteJournals = await getPublicJournals()
  const journals = remoteJournals.length > 0 ? remoteJournals : asFallbackJournals()
  const filtered = getFilteredJournals(journals, query)
  const stats = getJournalStats(journals)

  return (
    <div className="min-h-screen bg-muted/40 text-foreground">
      <SiteHeader />

      <main className="mx-auto max-w-7xl px-4 pb-16 pt-12 sm:px-6 lg:px-8">
        <section className="relative overflow-hidden rounded-3xl border border-border bg-card p-8 shadow-xl sm:p-10">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,hsl(var(--primary)/0.16),transparent_48%)]" />
          <div className="relative grid gap-8 lg:grid-cols-[1.2fr_1fr]">
            <div className="space-y-5">
              <Badge variant="secondary" className="gap-1.5 text-xs uppercase tracking-wider">
                <Sparkles className="h-3.5 w-3.5" />
                ScholarFlow Press
              </Badge>
              <h1 className="font-serif text-4xl font-semibold leading-tight text-foreground sm:text-5xl">
                Journals Across Disciplines, One Publishing Platform
              </h1>
              <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
                Browse our journal portfolio, review each title&apos;s scope, and jump directly to the latest published
                articles. This page is designed for readers, authors, and editorial partners.
              </p>
            </div>

            <div className="grid gap-3 rounded-2xl border border-border/80 bg-background/80 p-4 sm:grid-cols-3 lg:grid-cols-1">
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Total Journals</div>
                <div className="mt-1 text-2xl font-semibold">{stats.total}</div>
              </div>
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">With Impact Data</div>
                <div className="mt-1 text-2xl font-semibold">{stats.withImpact}</div>
              </div>
              <div className="rounded-xl border border-border/70 bg-card px-4 py-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Avg. Impact</div>
                <div className="mt-1 text-2xl font-semibold">{stats.avgImpact}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-border bg-card p-4 sm:p-5">
          <form method="get" className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Label htmlFor="journals-search" className="sr-only">
                Search journals by title, description, or ISSN
              </Label>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="journals-search"
                name="q"
                defaultValue={query}
                placeholder="Search journals by title, description, or ISSN…"
                autoComplete="off"
                className="pl-9"
              />
            </div>
            <Button type="submit" className="sm:w-auto">
              Search
            </Button>
            {query ? (
              <Button asChild variant="outline">
                <Link href="/journals">Clear</Link>
              </Button>
            ) : null}
          </form>
        </section>

        <section className="mt-8">
          {filtered.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center">
              <p className="text-lg font-medium text-foreground">No journals matched your search.</p>
              <p className="mt-2 text-sm text-muted-foreground">Try a broader keyword or clear the filter.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filtered.map((journal) => (
                <Link
                  key={journal.id}
                  href={`/journals/${journal.slug}`}
                  className="group flex h-full flex-col rounded-2xl border border-border bg-card p-5 shadow-sm transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg"
                >
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <Badge variant="outline" className="truncate">
                      {journal.issn || 'ISSN pending'}
                    </Badge>
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      IF {getJournalImpactLabel(journal.impact_factor)}
                    </span>
                  </div>

                  <h2 className="line-clamp-2 text-xl font-semibold leading-snug text-foreground transition-colors group-hover:text-primary">
                    {journal.title}
                  </h2>
                  <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                    {journal.description || 'Explore this journal profile and published articles.'}
                  </p>

                  <div className="mt-6 flex items-center justify-between border-t border-border/70 pt-4 text-sm">
                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                      <BookOpen className="h-4 w-4" />
                      Journal Profile
                    </span>
                    <span className="inline-flex items-center gap-1 font-semibold text-primary">
                      View
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
