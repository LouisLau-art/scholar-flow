"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export default function EnvironmentBanner() {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] flex h-8 items-center justify-center bg-yellow-400 text-xs font-bold text-black shadow-lg">
      Current Environment: UAT Staging (Not for Production)
    </div>
  )
}
