import { Suspense } from "react"
import { Metadata } from "next"
import { notFound } from "next/navigation"
import { IS_STAGING } from "@/lib/env"
import { FeedbackTable } from "./_components/FeedbackTable"
import { PageHeader } from "@/components/layout/PageHeader"

export const metadata: Metadata = {
  title: "UAT Feedback | Admin",
  description: "View and manage UAT feedback reports",
}

export default function AdminFeedbackPage() {
  if (!IS_STAGING) {
    notFound()
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="UAT Feedback"
        description="Review issues reported during User Acceptance Testing."
      />
      <Suspense fallback={<div>Loading feedback...</div>}>
        <FeedbackTable />
      </Suspense>
    </div>
  )
}
