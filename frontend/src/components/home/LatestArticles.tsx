"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Loader2, ArrowRight } from "lucide-react"

export default function LatestArticles() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const res = await fetch("/api/v1/manuscripts/published/latest?limit=6")
        const json = await res.json().catch(() => null)
        if (!cancelled && json?.success) setItems(Array.isArray(json.data) ? json.data : [])
      } catch (e) {
        if (!cancelled) setItems([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section className="py-20 border-t border-border/60 bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-10">
          <h2 className="text-3xl font-serif font-bold text-foreground">Latest Articles</h2>
          <Link href="/search?q=&mode=articles" className="text-sm font-bold text-primary hover:underline">
            View all
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading…</span>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-border bg-card p-12 text-center text-muted-foreground">
            No published articles yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((a) => (
              <Link
                key={a.id}
                href={`/articles/${a.id}`}
                className="group block rounded-3xl border border-border bg-card p-6 hover:border-primary/60 hover:shadow-xl transition-all"
              >
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                  {a.published_at ? new Date(a.published_at).toLocaleDateString() : "Published"}
                </div>
                <div className="mt-3 text-lg font-bold text-foreground group-hover:text-primary transition-colors line-clamp-2">
                  {a.title || "Untitled"}
                </div>
                <div className="mt-3 text-sm text-muted-foreground line-clamp-3">{a.abstract || ""}</div>
                <div className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-primary">
                  Read <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
