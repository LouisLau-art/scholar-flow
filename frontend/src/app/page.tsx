import { ArrowRight } from 'lucide-react'
import { Manrope, Playfair_Display } from 'next/font/google'
import Image from 'next/image'
import Link from 'next/link'

import SiteHeader from '@/components/layout/SiteHeader'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getBackendOrigin } from '@/lib/backend-origin'
import { formatDateLocal } from '@/lib/date-display'
import { cn } from '@/lib/utils'
import type { PublicArticle } from '@/services/portal'

const playfair = Playfair_Display({
  subsets: ['latin'],
  weight: ['600', '700'],
})

const manrope = Manrope({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
})

const heroStats = [
  { value: '3 million', label: 'monthly article views' },
  { value: '4,200', label: 'active reviewers' },
  { value: '12,000+', label: 'published papers' },
]

const actionCards = [
  {
    badge: 'Authors',
    title: 'Find a journal',
    description: 'Explore scope, APC, and editorial policies before submitting.',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?auto=format&fit=crop&w=1200&q=80',
  },
  {
    badge: 'Editors and reviewers',
    title: 'Find a topic',
    description: 'Browse thematic collections and open calls for papers.',
    href: '/topics',
    image: 'https://images.unsplash.com/photo-1497215842964-222b430dc094?auto=format&fit=crop&w=1200&q=80',
  },
  {
    badge: 'Resources for authors',
    title: 'Resources for authors',
    description: 'Use templates, checklists, and process guidance for submission.',
    href: '/journal/guidelines',
    image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1200&q=80',
  },
  {
    badge: 'Submission',
    title: 'Submit your research',
    description: 'Send your manuscript and track every workflow milestone.',
    href: '/submit',
    image: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80',
  },
  {
    badge: 'Peer review',
    title: 'Peer review',
    description: 'Manage assignments, comments, and final decisions in one place.',
    href: '/dashboard',
    image: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?auto=format&fit=crop&w=1200&q=80',
  },
]

const fallbackNews = [
  {
    id: 'fallback-1',
    title: 'Global food systems and climate resilience: a new perspective for policy makers',
    summary: 'A cross-disciplinary team proposes new policy levers for sustainable food systems.',
    category: 'Research news',
    dateLabel: 'Recently published',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1400&q=80',
  },
  {
    id: 'fallback-2',
    title: 'Ocean sensing maps reveal critical biodiversity hotspots at scale',
    summary: 'New sensor networks provide richer biodiversity signals for marine protection.',
    category: 'Earth science',
    dateLabel: 'Recently published',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1462547341486-6e0af4a6a574?auto=format&fit=crop&w=1400&q=80',
  },
  {
    id: 'fallback-3',
    title: 'Brain-inspired computing enters practical healthcare deployments',
    summary: 'Clinical teams report gains in diagnosis speed and explainability.',
    category: 'Neuroscience',
    dateLabel: 'Recently published',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1516117172878-fd2c41f4a759?auto=format&fit=crop&w=1400&q=80',
  },
  {
    id: 'fallback-4',
    title: 'Advanced materials improve grid storage reliability under stress',
    summary: 'Field tests show meaningful improvements for long-duration storage.',
    category: 'Energy',
    dateLabel: 'Recently published',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=1400&q=80',
  },
  {
    id: 'fallback-5',
    title: 'Machine-learning pipelines simplify translational medicine workflows',
    summary: 'Teams report faster turnaround and improved reproducibility.',
    category: 'Medical AI',
    dateLabel: 'Recently published',
    href: '/search?status=published',
    image: 'https://images.unsplash.com/photo-1511174511562-5f97f4f4a8d7?auto=format&fit=crop&w=1400&q=80',
  },
]

interface NewsCardData {
  id: string
  title: string
  summary: string
  category: string
  dateLabel: string
  href: string
  image: string
}

const HOME_LATEST_ARTICLES_LIMIT = 7
const HOME_LATEST_ARTICLES_REVALIDATE_SECONDS = 3600

async function getLatestArticlesServer(limit: number): Promise<PublicArticle[]> {
  try {
    const origin = getBackendOrigin()
    const res = await fetch(`${origin}/api/v1/portal/articles/latest?limit=${limit}`, {
      next: {
        revalidate: HOME_LATEST_ARTICLES_REVALIDATE_SECONDS,
        tags: ['portal-latest-articles'],
      },
    })
    if (!res.ok) return []

    const payload = await res.json().catch(() => null)
    if (Array.isArray(payload)) return payload as PublicArticle[]
    if (payload?.success && Array.isArray(payload?.data)) return payload.data as PublicArticle[]
    return []
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('Failed to load latest articles on server:', error)
    }
    return []
  }
}

function OverlayImage({
  src,
  className,
  overlayClassName,
  sizes = '100vw',
  eager = false,
}: {
  src: string
  className?: string
  overlayClassName: string
  sizes?: string
  eager?: boolean
}) {
  return (
    <div className={cn('relative overflow-hidden bg-muted', className)}>
      <Image
        src={src}
        alt=""
        aria-hidden="true"
        fill
        sizes={sizes}
        priority={eager}
        className="object-cover"
      />
      <div className={cn('pointer-events-none absolute inset-0', overlayClassName)} />
    </div>
  )
}

function NewsCard({
  item,
  featured = false,
  className,
}: {
  item: NewsCardData
  featured?: boolean
  className?: string
}) {
  return (
    <Link
      href={item.href}
      className={cn(
        'group overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg',
        className
      )}
    >
      <OverlayImage
        src={item.image}
        className={cn(featured ? 'h-64 sm:h-72' : 'h-44')}
        overlayClassName="bg-gradient-to-b from-foreground/15 to-foreground/60"
      />
      <div className={cn('p-4', featured && 'p-6')}>
        <p className="mb-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">{item.category}</p>
        <h3
          className={cn(
            playfair.className,
            'font-semibold leading-snug text-foreground transition-colors group-hover:text-primary',
            featured ? 'text-2xl' : 'line-clamp-2 text-lg'
          )}
        >
          {item.title}
        </h3>
        <p className={cn('mt-3 text-muted-foreground', featured ? 'line-clamp-3 text-base' : 'line-clamp-2 text-sm')}>
          {item.summary}
        </p>
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>{item.dateLabel}</span>
          <span className="inline-flex items-center gap-1 font-semibold text-primary">
            Read
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </div>
      </div>
    </Link>
  )
}

export default async function HomePage() {
  const articles = await getLatestArticlesServer(HOME_LATEST_ARTICLES_LIMIT)
  const newsItems: NewsCardData[] = articles.length === 0
    ? fallbackNews
    : articles.map((article, index) => ({
        id: article.id,
        title: article.title,
        summary: article.abstract || 'Read the latest peer-reviewed research and editorial highlights.',
        category: article.authors[0] || 'Latest research',
        dateLabel: article.published_at ? formatDateLocal(article.published_at) : 'Recently published',
        href: `/articles/${article.id}`,
        image: fallbackNews[index % fallbackNews.length].image,
      }))

  const featuredNews = newsItems[0]
  const secondaryNews = newsItems.slice(1)

  return (
    <div className={`min-h-screen bg-muted/40 text-foreground ${manrope.className} flex flex-col`}>
      <SiteHeader />

      <main className="flex-1">
        <section className="relative overflow-hidden bg-foreground text-white">
          <OverlayImage
            src="https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=2200&q=80"
            className="absolute inset-0"
            overlayClassName="bg-gradient-to-r from-foreground/85 to-primary/35"
            eager
          />
          <div className="relative mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6 sm:pt-28 lg:px-8">
            <div className="max-w-2xl">
              <p className="mb-4 text-xs uppercase tracking-[0.24em] text-primary-foreground/80">Frontiers-style academic portal</p>
              <h1 className={cn(playfair.className, 'text-4xl font-semibold tracking-tight sm:text-5xl')}>
                ScholarFlow Journal
              </h1>
              <p className={cn(playfair.className, 'mt-4 text-3xl font-semibold leading-tight text-white sm:text-5xl')}>
                Where scientists empower society
              </p>
              <p className="mt-5 max-w-xl text-base text-background/80 sm:text-lg">
                Creating trusted workflows for healthy science and faster publication outcomes.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link
                  href="/submit"
                  className="rounded-full bg-primary px-7 py-3 text-sm font-semibold text-white transition-all hover:bg-primary/90"
                >
                  Submit Manuscript
                </Link>
                <Link
                  href="/search?status=published"
                  className="rounded-full border border-white/40 px-7 py-3 text-sm font-semibold text-white transition-all hover:border-white hover:bg-card/10"
                >
                  Explore Latest Articles
                </Link>
              </div>
            </div>
            <div className="mt-16 grid gap-6 border-t border-white/20 pt-8 sm:grid-cols-3">
              {heroStats.map((item) => (
                <div key={item.label}>
                  <p className={cn(playfair.className, 'text-2xl font-semibold text-white sm:text-3xl')}>
                    {item.value}
                  </p>
                  <p className="mt-2 text-sm uppercase tracking-[0.14em] text-primary-foreground/80">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative -mt-8 z-10">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-3xl border border-border bg-card p-5 shadow-xl shadow-muted/30 sm:p-6">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                {actionCards.map((card) => (
                  <Link
                    key={card.title}
                    href={card.href}
                    className="group rounded-2xl border border-border bg-card p-3 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
                  >
                    <OverlayImage
                      src={card.image}
                      className="h-24 rounded-xl"
                      overlayClassName="bg-gradient-to-b from-foreground/10 to-foreground/35"
                    />
                    <p className="mt-4 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{card.badge}</p>
                    <h3 className="mt-2 text-lg font-semibold text-foreground transition-colors group-hover:text-primary">{card.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{card.description}</p>
                    <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary">
                      Go
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="pb-12 pt-14">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 className={cn(playfair.className, 'text-4xl font-semibold text-foreground')}>
                  News
                </h2>
                <p className="mt-2 text-base text-muted-foreground">Latest Articles from ScholarFlow Journal</p>
              </div>
              <Link href="/search?status=published" className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary">
                See more news
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {featuredNews ? (
              <div className="grid gap-4 lg:grid-cols-3">
                <NewsCard item={featuredNews} featured className="lg:col-span-2" />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                  {secondaryNews.slice(0, 2).map((item) => (
                    <NewsCard key={item.id} item={item} />
                  ))}
                </div>
              </div>
            ) : (
              <p className="rounded-2xl border border-dashed border-border/80 bg-card p-8 text-center text-muted-foreground">
                Latest Articles will appear here soon.
              </p>
            )}
            {secondaryNews.length > 2 && (
              <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {secondaryNews.slice(2, 8).map((item) => (
                  <NewsCard key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="mt-4 bg-primary py-16 text-white">
          <div className="mx-auto max-w-5xl px-4 text-center sm:px-6">
            <p className="text-xs uppercase tracking-[0.22em] text-primary-foreground/80">Newsletter</p>
            <h3 className={cn(playfair.className, 'mt-3 text-3xl font-semibold')}>
              Get the latest research updates, subscribe to our newsletter
            </h3>
            <form className="mx-auto mt-8 grid max-w-3xl gap-3 md:grid-cols-3">
              <Label htmlFor="newsletter-first-name" className="sr-only">
                First name
              </Label>
              <Input
                id="newsletter-first-name"
                type="text"
                placeholder="Name"
                autoComplete="given-name"
                className="h-11 border-white/35 bg-card/10 px-4 text-sm text-white placeholder:text-primary-foreground/80 focus-visible:border-white focus-visible:ring-white/60"
              />
              <Label htmlFor="newsletter-last-name" className="sr-only">
                Last name
              </Label>
              <Input
                id="newsletter-last-name"
                type="text"
                placeholder="Last name"
                autoComplete="family-name"
                className="h-11 border-white/35 bg-card/10 px-4 text-sm text-white placeholder:text-primary-foreground/80 focus-visible:border-white focus-visible:ring-white/60"
              />
              <Label htmlFor="newsletter-email" className="sr-only">
                Email
              </Label>
              <Input
                id="newsletter-email"
                type="email"
                placeholder="Email"
                autoComplete="email"
                className="h-11 border-white/35 bg-card/10 px-4 text-sm text-white placeholder:text-primary-foreground/80 focus-visible:border-white focus-visible:ring-white/60"
              />
              <button
                type="button"
                className="mx-auto mt-2 inline-flex h-10 items-center justify-center rounded-full bg-card px-8 text-sm font-semibold text-primary transition-colors hover:bg-primary/10 md:col-span-3"
              >
                Subscribe
              </button>
            </form>
          </div>
        </section>
      </main>
    </div>
  )
}
