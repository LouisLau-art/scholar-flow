'use client'

import { useEffect, useState } from 'react'
import DOMPurify from 'isomorphic-dompurify'
import SiteHeader from '@/components/layout/SiteHeader'

type PageData = {
  slug: string
  title: string
  content?: string | null
}

export default function CmsPageClient({ slug }: { slug: string }) {
  const [page, setPage] = useState<PageData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const res = await fetch(`/api/v1/cms/pages/${encodeURIComponent(slug)}`)
        if (!res.ok) {
          setPage(null)
          return
        }
        const body = await res.json()
        if (body?.success && body?.data) {
          setPage(body.data as PageData)
        } else {
          setPage(null)
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [slug])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <SiteHeader />
        <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-600">Loading…</div>
        </main>
      </div>
    )
  }

  if (!page) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <SiteHeader />
        <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-700">Page not found.</div>
        </main>
      </div>
    )
  }

  const html = DOMPurify.sanitize(page.content || '', { USE_PROFILES: { html: true } })

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <article className="bg-white rounded-3xl shadow-sm border border-slate-100 p-8">
          <h1 className="font-serif text-4xl font-bold text-slate-900">{page.title}</h1>
          <div className="mt-8 prose max-w-none text-slate-800" dangerouslySetInnerHTML={{ __html: html }} />
        </article>
      </main>
    </div>
  )
}

