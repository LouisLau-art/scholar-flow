'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ArrowLeft, LogOut } from 'lucide-react'

function buildExitHref(pathname: string): string {
  if (pathname.startsWith('/reviewer/workspace/')) {
    return '/dashboard'
  }
  return '/'
}

export default function ReviewerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '/'
  const exitHref = buildExitHref(pathname)

  return (
    <div className="min-h-screen bg-muted/40">
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="text-sm font-semibold tracking-wide text-foreground">Reviewer Workspace</div>
          <Link
            href={exitHref}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted"
          >
            {pathname.startsWith('/reviewer/workspace/') ? <ArrowLeft className="h-4 w-4" /> : <LogOut className="h-4 w-4" />}
            Exit
          </Link>
        </div>
      </header>
      {children}
    </div>
  )
}
