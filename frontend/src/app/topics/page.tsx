import SiteHeader from '@/components/layout/SiteHeader'
import { Stethoscope, Cpu, FlaskConical, Landmark, ArrowRight, Globe } from 'lucide-react'
import Link from 'next/link'

export const revalidate = 300

type TopicItem = {
  id: string
  name: string
  icon?: string | null
  count?: number | null
  query?: string | null
  metric_label?: string | null
}

const iconMap: Record<string, typeof Globe> = {
  Stethoscope,
  Cpu,
  FlaskConical,
  Landmark,
}

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_ORIGIN ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  return raw.replace(/\/$/, '')
}

async function getTopicsServer(): Promise<TopicItem[]> {
  try {
    const origin = getBackendOrigin()
    const response = await fetch(`${origin}/api/v1/public/topics`, {
      next: {
        revalidate,
        tags: ['public-topics'],
      },
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || !payload?.success || !Array.isArray(payload?.data)) {
      return []
    }
    return payload.data as TopicItem[]
  } catch {
    return []
  }
}

export default async function TopicsPage() {
  const topics = await getTopicsServer()

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-16 sm:px-6 lg:px-8">
        <header className="mb-16">
          <h1 className="text-4xl font-serif font-bold text-foreground mb-4 tracking-tight">Explore by Subject</h1>
          <p className="text-lg text-muted-foreground font-medium">Browse published research collections by subject area.</p>
        </header>

        {topics.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-border bg-card p-10 text-center text-muted-foreground">
            No topic collections available.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {topics.map((topic) => {
              const Icon = iconMap[String(topic.icon || '')] || Globe
              const query = String(topic.query || topic.name || '').trim()
              return (
                <Link
                  key={topic.id}
                  href={`/search?mode=articles&q=${encodeURIComponent(query)}`}
                  className="group bg-card p-8 rounded-3xl shadow-sm ring-1 ring-border hover:shadow-2xl hover:ring-primary/30 hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="bg-primary/10 w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-primary transition-colors">
                    <Icon className="h-7 w-7 text-primary group-hover:text-primary-foreground" />
                  </div>
                  <h3 className="text-xl font-bold text-foreground mb-2">{topic.name}</h3>
                  <div className="flex items-center justify-between mt-4">
                    <span className="text-sm font-bold text-muted-foreground uppercase">
                      {Number(topic.count || 0)} {topic.metric_label || 'Articles'}
                    </span>
                    <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
