"use client"

import * as React from "react"
import dynamic from "next/dynamic"
import { IS_STAGING } from "@/lib/env"

// Dynamically import UAT components to enable tree-shaking in Production
const EnvironmentBanner = dynamic(() => import("@/components/uat/EnvironmentBanner"), {
  ssr: true, // Banner is simple, SSR is fine
})

const FeedbackWidget = dynamic(() => import("@/components/uat/FeedbackWidget"), {
  ssr: false, // Widget is interactive and client-only
})

export function EnvironmentProvider({ children }: { children: React.ReactNode }) {
  // If not staging, just render children. 
  // Next.js compiler + Terser should eliminate the dead code path for the imports if IS_STAGING is hardcoded false at build time.
  // However, since IS_STAGING is process.env based, it works.
  
  if (!IS_STAGING) {
    return <>{children}</>
  }

  return (
    <>
      <EnvironmentBanner />
      {children}
      <FeedbackWidget />
    </>
  )
}
