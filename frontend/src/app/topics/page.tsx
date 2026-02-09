'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { Stethoscope, Cpu, FlaskConical, Landmark, ArrowRight, Loader2, Globe } from 'lucide-react'
import Link from 'next/link'

const iconMap: any = {
  Stethoscope: Stethoscope,
  Cpu: Cpu,
  FlaskConical: FlaskConical,
  Landmark: Landmark,
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchTopics() {
      try {
        const res = await fetch('/api/v1/public/topics')
        const result = await res.json()
        if (result.success) setTopics(result.data)
      } catch (err) {
        console.error('Failed to load topics:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchTopics()
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-16 sm:px-6 lg:px-8">
        <header className="mb-16">
          <h1 className="text-4xl font-serif font-bold text-slate-900 mb-4 tracking-tight">Explore by Subject</h1>
          <p className="text-lg text-slate-500 font-medium">Browse published research collections by subject area.</p>
        </header>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {topics.map((topic) => {
              const Icon = iconMap[topic.icon] || Globe
              return (
                <Link 
                  key={topic.id} 
                  href={`/search?mode=articles&q=${encodeURIComponent(topic.query || topic.name)}`}
                  className="group bg-white p-8 rounded-3xl shadow-sm ring-1 ring-slate-200 hover:shadow-2xl hover:ring-blue-500/30 hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="bg-blue-50 w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-blue-600 transition-colors">
                    <Icon className="h-7 w-7 text-blue-600 group-hover:text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">{topic.name}</h3>
                  <div className="flex items-center justify-between mt-4">
                    <span className="text-sm font-bold text-slate-400 uppercase">{topic.count} {topic.metric_label || 'Articles'}</span>
                    <ArrowRight className="h-5 w-5 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
