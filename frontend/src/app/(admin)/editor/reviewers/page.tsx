'use client'

import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'
import { ReviewerLibraryList } from '@/components/editor/ReviewerLibraryList'
import { ArrowLeft, Users } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function ReviewerLibraryPage() {
  return (
    <div className="sf-page-shell">
      <SiteHeader />
      <main className="sf-page-container space-y-6 py-10">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-card p-2 shadow-sm ring-1 ring-border">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-foreground tracking-tight">Reviewer Library</h1>
              <p className="mt-1 text-muted-foreground font-medium">
                Build your reviewer pool without sending invitations.
              </p>
            </div>
          </div>

          <Link href="/dashboard" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <ReviewerLibraryList />
      </main>
    </div>
  )
}
