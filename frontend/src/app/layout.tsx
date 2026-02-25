import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ErrorBoundary from '@/components/ErrorBoundary'
import Toast from '@/components/Toast'
import QueryProvider from '@/components/providers/QueryProvider'
import { ConditionalSiteFooter } from '@/components/layout/ConditionalSiteFooter'

import { EnvironmentProvider } from '@/components/providers/EnvironmentProvider'
import { ThemeProvider } from '@/components/providers/ThemeProvider'

const inter = Inter({ subsets: ['latin'] })
const DEFAULT_SITE_URL = 'http://localhost:3000'

function resolveSiteUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.VERCEL_PROJECT_PRODUCTION_URL ||
    process.env.VERCEL_URL ||
    DEFAULT_SITE_URL
  const normalized = raw.trim().replace(/\/$/, '')
  if (!normalized) return DEFAULT_SITE_URL
  return /^https?:\/\//i.test(normalized) ? normalized : `https://${normalized}`
}

const siteUrl = resolveSiteUrl()
const metadataBase = (() => {
  try {
    return new URL(siteUrl)
  } catch {
    return new URL(DEFAULT_SITE_URL)
  }
})()
const ogImageUrl = new URL('/og-image.png', metadataBase).toString()
const twitterCreator = process.env.NEXT_PUBLIC_TWITTER_CREATOR?.trim() || undefined

function resolveVerification(): Metadata['verification'] | undefined {
  const google = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION?.trim()
  const yandex = process.env.NEXT_PUBLIC_YANDEX_SITE_VERIFICATION?.trim()
  const bing = process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION?.trim()

  if (!google && !yandex && !bing) return undefined

  const verification: NonNullable<Metadata['verification']> = {}
  if (google) verification.google = google
  if (yandex) verification.yandex = yandex
  if (bing) verification.other = { bing }
  return verification
}

const verification = resolveVerification()

export const metadata: Metadata = {
  metadataBase,
  title: {
    default: 'ScholarFlow | Frontiers-inspired Academic Workflow Platform',
    template: '%s | ScholarFlow'
  },
  description: 'ScholarFlow is an AI-powered academic workflow platform that streamlines manuscript submission, peer review, and publication processes with Frontiers-inspired design.',
  keywords: ['academic publishing', 'peer review', 'manuscript submission', 'AI research tools', 'scholarly workflow'],
  
  // Open Graph metadata for social sharing
  openGraph: {
    type: 'website',
    url: siteUrl,
    title: 'ScholarFlow | Frontiers-inspired Academic Workflow Platform',
    description: 'AI-powered platform for academic manuscript submission, peer review, and publication.',
    siteName: 'ScholarFlow',
    images: [
      {
        url: ogImageUrl,
        width: 1200,
        height: 630,
        alt: 'ScholarFlow Academic Workflow Platform',
      },
    ],
    locale: 'en_US',
  },
  
  // Twitter Card metadata
  twitter: {
    card: 'summary_large_image',
    title: 'ScholarFlow | Frontiers-inspired Academic Workflow Platform',
    description: 'AI-powered platform for academic manuscript submission, peer review, and publication.',
    images: [ogImageUrl],
    ...(twitterCreator ? { creator: twitterCreator } : {}),
  },
  
  // Additional SEO metadata
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  
  ...(verification ? { verification } : {}),
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ErrorBoundary>
            <QueryProvider>
              <EnvironmentProvider>
                {children}
              </EnvironmentProvider>
            </QueryProvider>
          </ErrorBoundary>
          <ConditionalSiteFooter />
          <Toast />
        </ThemeProvider>
      </body>
    </html>
  )
}
