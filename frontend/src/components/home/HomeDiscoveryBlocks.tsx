'use client'

import { Stethoscope, Cpu, FlaskConical, Gavel, Landmark, Palette, Globe2, Atom } from 'lucide-react'
import Link from 'next/link'

const stats = [
  { label: 'Journals', value: '240+' },
  { label: 'Active Reviewers', value: '12,500+' },
  { label: 'Annual Citations', value: '2.4M' },
  { label: 'Open Access Articles', value: '180K+' },
]

const subjects = [
  { name: 'Medicine', icon: Stethoscope, count: 42, color: 'text-destructive bg-destructive/10' },
  { name: 'Technology', icon: Cpu, count: 38, color: 'text-primary bg-primary/10' },
  { name: 'Life Sciences', icon: FlaskConical, count: 31, color: 'text-primary bg-primary/10' },
  { name: 'Physics', icon: Atom, count: 25, color: 'text-indigo-600 bg-indigo-50' },
  { name: 'Social Sciences', icon: Landmark, count: 22, color: 'text-secondary-foreground bg-secondary' },
  { name: 'Legal', icon: Gavel, count: 15, color: 'text-muted-foreground bg-muted' },
  { name: 'Arts & Design', icon: Palette, count: 12, color: 'text-foreground bg-muted' },
  { name: 'Global Studies', icon: Globe2, count: 18, color: 'text-cyan-600 bg-cyan-50' },
]

export default function HomeDiscoveryBlocks() {
  return (
    <div className="bg-background">
      {/* Stats Banner */}
      <div className="bg-foreground py-12 relative overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl sm:text-4xl font-mono font-bold text-primary-foreground mb-1">{s.value}</div>
                <div className="text-sm font-bold text-primary-foreground/60 uppercase tracking-widest">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Subject Area Grid */}
      <section className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-serif font-bold text-foreground">Explore by Subject</h2>
            <p className="mt-4 text-muted-foreground font-medium text-lg">Browse our journals categorized by research area.</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
            {subjects.map((sub) => (
              <Link
                key={sub.name}
                href={`/search?mode=journals&q=${encodeURIComponent(sub.name)}`}
                className="group block rounded-3xl border border-border/60 bg-card p-8 transition-all duration-300 hover:-translate-y-1 hover:border-primary/60 hover:shadow-2xl"
              >
                <div className={`${sub.color} w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <sub.icon className="h-7 w-7" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-1">{sub.name}</h3>
                <p className="text-sm text-muted-foreground font-medium">{sub.count} Journals</p>
              </Link>
            ))}
          </div>
          
          <div className="mt-16 text-center">
            <Link
              href="/topics"
              className="inline-flex items-center justify-center rounded-full bg-primary px-8 py-4 font-bold text-primary-foreground shadow-lg transition-colors hover:bg-primary/90"
            >
              View All Topics & Areas
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
