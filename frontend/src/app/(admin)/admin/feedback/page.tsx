import { Suspense } from "react"
import { Metadata } from "next"
import { notFound } from "next/navigation"
import { IS_STAGING } from "@/lib/env"
import { FeedbackTable } from "./_components/FeedbackTable"
import { PageHeader } from "@/components/layout/PageHeader"
import SiteHeader from "@/components/layout/SiteHeader"

export const metadata: Metadata = {
  title: "UAT Feedback | Admin",
  description: "View and manage UAT feedback reports",
}

export default function AdminFeedbackPage() {
  if (!IS_STAGING) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6">
          <PageHeader
            title="UAT Feedback"
            description="Review issues reported during User Acceptance Testing."
          />
          <Suspense fallback={<div>Loading feedback...</div>}>
            <FeedbackTable />
          </Suspense>
        </div>
      </main>
    </div>
  )
}
