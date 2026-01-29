'use client'

import React, { useCallback } from 'react'
import useEmblaCarousel from 'embla-carousel-react'
import Autoplay from 'embla-carousel-autoplay'
import { ChevronLeft, ChevronRight, Star } from 'lucide-react'
import Link from 'next/link'
import { demoJournals } from '@/lib/demo-journals'

export default function JournalCarousel() {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, align: 'start' }, [Autoplay({ delay: 4000 })])

  const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi])
  const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi])

  return (
    <section className="py-20 bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-end justify-between mb-12">
          <div>
            <h2 className="text-3xl font-serif font-bold text-slate-900">Featured Journals</h2>
            <p className="mt-2 text-slate-500 font-medium text-lg">Explore high-impact research across diverse domains.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={scrollPrev} className="p-3 rounded-full bg-white shadow-md hover:bg-slate-50 text-slate-600 border border-slate-200 transition-all">
              <ChevronLeft className="h-6 w-6" />
            </button>
            <button onClick={scrollNext} className="p-3 rounded-full bg-white shadow-md hover:bg-slate-50 text-slate-600 border border-slate-200 transition-all">
              <ChevronRight className="h-6 w-6" />
            </button>
          </div>
        </div>

        <div className="overflow-hidden" ref={emblaRef}>
          <div className="flex gap-6">
            {demoJournals.map((j) => (
              <div key={j.id} className="flex-[0_0_85%] sm:flex-[0_0_45%] lg:flex-[0_0_30%] min-w-0">
                <div className="group h-full p-8 rounded-3xl border border-slate-200 bg-white text-slate-900 shadow-sm hover:shadow-md hover:border-blue-200 transition-shadow duration-300">
                  <div className={`${j.color} w-16 h-1 w-full rounded-full mb-6 group-hover:scale-x-110 transition-transform`} />
                  <div className="flex items-center gap-2 text-blue-600 font-bold text-xs uppercase tracking-widest mb-4">
                    <Star className="h-3 w-3 fill-current" /> {j.category}
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-4 font-serif leading-snug min-h-[3.5rem]">
                    {j.title}
                  </h3>
                  <div className="flex items-center justify-between mt-auto pt-6 border-t border-slate-100">
                    <div>
                      <span className="text-xs text-slate-400 font-bold block uppercase">Impact Factor</span>
                      <span className="text-lg font-mono font-bold text-slate-900">{j.impact}</span>
                    </div>
                    <Link href={`/journals/${j.slug}`} className="text-sm font-bold text-blue-600 hover:text-blue-800 transition-colors">
                      Learn More →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
