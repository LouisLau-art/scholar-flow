'use client'

import Link from 'next/link'
import { Mail, Phone, MapPin, MessageSquare } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'

export default function ContactPage() {
  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <SiteHeader />

      <main className="flex-1">
        <section className="bg-foreground py-20 text-background">
          <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
            <h1 className="text-4xl font-serif font-bold tracking-tight">Contact Editorial Office</h1>
            <p className="mt-4 max-w-2xl text-background/80">
              For submission support, editorial workflow questions, and publication inquiries, use the channels below.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid gap-4 md:grid-cols-3">
            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Mail className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-foreground">Email</h2>
              <p className="mt-2 text-sm text-muted-foreground">editorial@scholarflow.org</p>
            </article>

            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Phone className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-foreground">Phone</h2>
              <p className="mt-2 text-sm text-muted-foreground">+1 (555) 102-2048</p>
            </article>

            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <MapPin className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-foreground">Office</h2>
              <p className="mt-2 text-sm text-muted-foreground">Global Research Hub, Academic District</p>
            </article>
          </div>

          <div className="mt-8 rounded-2xl border border-border bg-card p-6">
            <h3 className="text-xl font-serif font-semibold text-foreground">Need quick help?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Include manuscript ID, journal, and your role in the message so the team can route your ticket faster.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <a
                href="mailto:editorial@scholarflow.org?subject=ScholarFlow%20Support"
                className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
              >
                <MessageSquare className="h-4 w-4" />
                Send Email
              </a>
              <Link
                href="/journal/contact"
                className="inline-flex items-center rounded-full border border-border bg-card px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-muted/50"
              >
                CMS Contact Page
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
