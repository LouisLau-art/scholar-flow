'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { getCmsMenu } from '@/services/cms'

type LinkItem = { label: string; href: string }

export default function SiteFooter() {
  const [items, setItems] = useState<LinkItem[] | null>(null)

  const fallback = useMemo<LinkItem[]>(
    () => [
      { label: 'About', href: '/journal/about' },
      { label: 'Guidelines', href: '/journal/guidelines' },
      { label: 'Contact', href: '/journal/contact' },
      { label: 'Ethics', href: '/journal/ethics' },
    ],
    []
  )

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const raw = await getCmsMenu('footer')
        const parsed: LinkItem[] = (raw || [])
          .map((i: any) => {
            const label = String(i?.label || '').trim()
            const href = i?.page_slug ? `/journal/${i.page_slug}` : String(i?.url || '').trim()
            if (!label || !href) return null
            return { label, href }
          })
          .filter(Boolean) as LinkItem[]
        if (mounted) setItems(parsed.length > 0 ? parsed : [])
      } catch {
        if (mounted) setItems(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  const links = items === null ? fallback : items.length > 0 ? items : fallback

  return (
    <footer className="border-t border-slate-800 bg-slate-900 text-slate-200">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="font-serif text-xl font-bold text-white">ScholarFlow</div>
            <div className="mt-1 text-sm text-slate-400">Modern academic workflow platform.</div>
          </div>

          <nav className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-slate-300">
            {links.map((link) => (
              <Link key={link.href} href={link.href} className="hover:text-white">
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="mt-10 text-xs text-slate-500">
          © {new Date().getFullYear()} ScholarFlow. All rights reserved.
        </div>
      </div>
    </footer>
  )
}

