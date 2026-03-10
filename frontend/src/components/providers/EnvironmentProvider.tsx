"use client"

import * as React from "react"
import dynamic from "next/dynamic"
import { IS_STAGING, isRuntimeStagingHost } from "@/lib/env"

// Dynamically import UAT components to enable tree-shaking in Production
const EnvironmentBanner = dynamic(() => import("@/components/uat/EnvironmentBanner"), {
  ssr: true, // Banner is simple, SSR is fine
})

const FeedbackWidget = dynamic(() => import("@/components/uat/FeedbackWidget"), {
  ssr: false, // Widget is interactive and client-only
})

export function EnvironmentProvider({ children }: { children: React.ReactNode }) {
  const [isStaging, setIsStaging] = React.useState(IS_STAGING)

  React.useEffect(() => {
    if (IS_STAGING || typeof window === "undefined") return
    const runtimeHost = `${window.location.hostname} ${window.location.href}`
    if (isRuntimeStagingHost(runtimeHost)) {
      setIsStaging(true)
    }
  }, [])

  // 如果构建时环境变量没显式标记 staging，则在客户端按当前域名补判一次。
  // 这样 Vercel 上的 UAT 域名不会因为缺失 NEXT_PUBLIC_APP_ENV 而丢失横幅/反馈组件。
  if (!isStaging) {
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
