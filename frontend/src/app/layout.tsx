import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ErrorBoundary from '@/components/ErrorBoundary'
import Toast from '@/components/Toast'
import SiteFooter from '@/components/layout/SiteFooter'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'ScholarFlow | Frontiers-inspired Academic Workflow Platform',
    template: '%s | ScholarFlow'
  },
  description: 'ScholarFlow is an AI-powered academic workflow platform that streamlines manuscript submission, peer review, and publication processes with Frontiers-inspired design.',
  keywords: ['academic publishing', 'peer review', 'manuscript submission', 'AI research tools', 'scholarly workflow'],
  
  // Open Graph metadata for social sharing
  openGraph: {
    type: 'website',
    url: 'https://scholarflow.example.com',
    title: 'ScholarFlow | Frontiers-inspired Academic Workflow Platform',
    description: 'AI-powered platform for academic manuscript submission, peer review, and publication.',
    siteName: 'ScholarFlow',
    images: [
      {
        url: 'https://scholarflow.example.com/og-image.png',
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
    images: ['https://scholarflow.example.com/og-image.png'],
    creator: '@scholarflow',
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
  
  // Verification codes for search engines
  verification: {
    google: 'google-site-verification-code',
    yandex: 'yandex-verification-code',
    bing: 'bing-verification-code',
  },
  
  // Favicon and icons
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
    other: [
      {
        rel: 'icon',
        url: '/favicon-32x32.png',
        sizes: '32x32',
      },
    ],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
        <SiteFooter />
        <Toast />
      </body>
    </html>
  )
}
