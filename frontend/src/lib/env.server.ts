import { APP_ENV, isKnownStagingHost } from './env'

const SERVER_DEPLOY_HOST_HINTS = [
  process.env.NEXT_PUBLIC_SITE_URL,
  process.env.VERCEL_PROJECT_PRODUCTION_URL,
  process.env.VERCEL_URL,
]
  .filter(Boolean)
  .map((value) => String(value).trim().toLowerCase())

export const IS_SERVER_STAGING =
  APP_ENV === 'staging' || SERVER_DEPLOY_HOST_HINTS.some(isKnownStagingHost)
