const APP_ENV = (process.env.NEXT_PUBLIC_APP_ENV || 'development').trim().toLowerCase()

const DEPLOY_HOST_HINTS = [
  process.env.NEXT_PUBLIC_SITE_URL,
  process.env.VERCEL_PROJECT_PRODUCTION_URL,
  process.env.VERCEL_URL,
]
  .filter(Boolean)
  .map((value) => String(value).trim().toLowerCase())

export function isKnownStagingHost(value: string): boolean {
  if (!value) return false
  return (
    value.includes('scholar-flow-q1yw.vercel.app') ||
    value.includes('q1yw.vercel.app') ||
    value.includes('uat') ||
    value.includes('staging')
  )
}

export const IS_STAGING = APP_ENV === 'staging' || DEPLOY_HOST_HINTS.some(isKnownStagingHost)

export function isRuntimeStagingHost(hostOrUrl: string | null | undefined): boolean {
  return isKnownStagingHost(String(hostOrUrl || '').trim().toLowerCase())
}

export { APP_ENV }
