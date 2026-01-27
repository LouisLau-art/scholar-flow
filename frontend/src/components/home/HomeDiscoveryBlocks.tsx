'use client'

import { Stethoscope, Cpu, FlaskConical, Gavel, Landmark, Palette, Globe2, Atom } from 'lucide-react'

const stats = [
  { label: 'Journals', value: '240+' },
  { label: 'Active Reviewers', value: '12,500+' },
  { label: 'Annual Citations', value: '2.4M' },
  { label: 'Open Access Articles', value: '180K+' },
]

const subjects = [
  { name: 'Medicine', icon: Stethoscope, count: 42, color: 'text-rose-600 bg-rose-50' },
  { name: 'Technology', icon: Cpu, count: 38, color: 'text-blue-600 bg-blue-50' },
  { name: 'Life Sciences', icon: FlaskConical, count: 31, color: 'text-emerald-600 bg-emerald-50' },
  { name: 'Physics', icon: Atom, count: 25, color: 'text-indigo-600 bg-indigo-50' },
  { name: 'Social Sciences', icon: Landmark, count: 22, color: 'text-amber-600 bg-amber-50' },
  { name: 'Legal', icon: Gavel, count: 15, color: 'text-slate-600 bg-slate-50' },
  { name: 'Arts & Design', icon: Palette, count: 12, color: 'text-purple-600 bg-purple-50' },
  { name: 'Global Studies', icon: Globe2, count: 18, color: 'text-cyan-600 bg-cyan-50' },
]

export default function HomeDiscoveryBlocks() {
  return (
    <div className="bg-white">
      {/* Stats Banner */}
      <div className="bg-slate-900 py-12 relative overflow-hidden">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl sm:text-4xl font-mono font-bold text-white mb-1">{s.value}</div>
                <div className="text-sm font-bold text-slate-400 uppercase tracking-widest">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Subject Area Grid */}
      <section className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-serif font-bold text-slate-900">Explore by Subject</h2>
            <p className="mt-4 text-slate-500 font-medium text-lg">Browse our journals categorized by research area.</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
            {subjects.map((sub) => (
              <div key={sub.name} className="group cursor-pointer p-8 rounded-3xl border border-slate-100 bg-white hover:border-blue-500 hover:shadow-2xl hover:-translate-y-1 transition-all duration-300">
                <div className={`${sub.color} w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <sub.icon className="h-7 w-7" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">{sub.name}</h3>
                <p className="text-sm text-slate-400 font-medium">{sub.count} Journals</p>
              </div>
            ))}
          </div>
          
          <div className="mt-16 text-center">
            <button className="px-8 py-4 rounded-full bg-slate-900 text-white font-bold hover:bg-slate-800 transition-colors shadow-lg">
              View All Topics & Areas
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
