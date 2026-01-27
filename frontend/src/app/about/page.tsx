'use client'

import SiteHeader from '@/components/layout/SiteHeader'
import { Globe, ShieldCheck, Zap, Users, MessageSquare } from 'lucide-react'

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <SiteHeader />
      
      <main className="flex-1">
        {/* About Hero */}
        <section className="bg-slate-900 text-white py-24 relative overflow-hidden">
          <div className="absolute inset-0 opacity-10 bg-grid-slate pointer-events-none" />
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10 text-center">
            <h1 className="text-5xl font-serif font-bold mb-6 tracking-tight">Our Mission: Open Science</h1>
            <p className="mx-auto max-w-2xl text-xl text-slate-400 italic">
              ScholarFlow is dedicated to accelerating scientific discovery by making research freely accessible 
              and peer review transparent and efficient.
            </p>
          </div>
        </section>

        {/* Values Grid */}
        <section className="py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              <div className="text-center p-8 bg-slate-50 rounded-3xl border border-slate-100 shadow-sm">
                <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <ShieldCheck className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-4">Rigorous Review</h3>
                <p className="text-slate-500">Every manuscript undergoes triple-blind peer review by global experts in the field.</p>
              </div>
              <div className="text-center p-8 bg-slate-50 rounded-3xl border border-slate-100 shadow-sm">
                <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <Zap className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-4">AI-Enhanced</h3>
                <p className="text-slate-500">We leverage cutting-edge LLMs to parse metadata and recommend the most suitable reviewers.</p>
              </div>
              <div className="text-center p-8 bg-slate-50 rounded-3xl border border-slate-100 shadow-sm">
                <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <Users className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-4">Global Community</h3>
                <p className="text-slate-500">Join a network of over 12,500 active researchers and editors worldwide.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section className="bg-slate-50 py-20 border-t border-slate-200">
          <div className="mx-auto max-w-3xl px-4 text-center">
            <h2 className="text-3xl font-serif font-bold text-slate-900 mb-8">Get in Touch</h2>
            <div className="flex justify-center gap-8 mb-12">
              <div className="flex items-center gap-2 text-slate-600">
                <Mail className="h-5 w-5 text-blue-600" /> support@scholarflow.org
              </div>
              <div className="flex items-center gap-2 text-slate-600">
                <Globe className="h-5 w-5 text-blue-600" /> Global Research HQ
              </div>
            </div>
            <button className="flex items-center gap-2 mx-auto px-8 py-4 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-all">
              <MessageSquare className="h-5 w-5" /> Contact Editorial Office
            </button>
          </div>
        </section>
      </main>
    </div>
  )
}

import { Mail } from 'lucide-react'
