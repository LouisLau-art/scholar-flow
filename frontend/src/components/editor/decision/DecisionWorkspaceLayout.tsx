'use client'

import type { ReactNode } from 'react'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

type DecisionWorkspaceLayoutProps = {
  manuscriptTitle: string
  manuscriptStatus?: string | null
  manuscriptId: string
  left: ReactNode
  middle: ReactNode
  right: ReactNode
}

export function DecisionWorkspaceLayout({
  manuscriptTitle,
  manuscriptStatus,
  manuscriptId,
  left,
  middle,
  right,
}: DecisionWorkspaceLayoutProps) {
  return (
    <main className="min-h-screen bg-muted/40">
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-[1700px] items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Final Decision Workspace</p>
            <h1 className="truncate text-lg font-semibold text-foreground sm:text-xl">{manuscriptTitle}</h1>
            {manuscriptStatus ? (
              <p className="text-xs text-muted-foreground">Current status: {manuscriptStatus}</p>
            ) : null}
          </div>
          <Link
            href={`/editor/manuscript/${encodeURIComponent(manuscriptId)}`}
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            返回稿件详情
          </Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1700px] grid-cols-1 gap-4 px-4 py-4 md:grid-cols-12 sm:px-6">
        <section className="md:col-span-5 lg:col-span-5">{left}</section>
        <section className="md:col-span-4 lg:col-span-4">{middle}</section>
        <section className="md:col-span-3 lg:col-span-3">{right}</section>
      </div>
    </main>
  )
}
