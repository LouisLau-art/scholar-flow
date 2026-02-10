'use client'

import { usePathname } from 'next/navigation'
import { SiteFooter } from '@/components/portal/SiteFooter'

const INTERNAL_PREFIXES = ['/editor', '/admin', '/dashboard', '/finance', '/proofreading', '/reviewer', '/review']

export function ConditionalSiteFooter() {
  const pathname = usePathname() || ''
  const hideFooter = INTERNAL_PREFIXES.some((prefix) => pathname.startsWith(prefix))
  if (hideFooter) return null
  return <SiteFooter />
}

