'use client'

import SiteHeader from '@/components/layout/SiteHeader'
import HeroSection from '@/components/home/HeroSection'
import JournalCarousel from '@/components/home/JournalCarousel'
import HomeDiscoveryBlocks from '@/components/home/HomeDiscoveryBlocks'
import LatestArticles from '@/components/home/LatestArticles'
import Link from 'next/link'
import { FileText, Settings, ShieldCheck, DollarSign, ChevronRight } from 'lucide-react'

export default function HomePage() {
  /**
   * 学术门户重构首页 (003-portal-redesign)
   * 遵循 v1.8.0 章程: Frontiers 视觉标准, 全栈切片原则
   */
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <SiteHeader />
      
      <main className="flex-1">
        <HeroSection />
        
        {/* Quick Access Dashboard Tiles (Portal Overlay) */}
        <div className="relative -mt-12 z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Link href="/submit" className="flex items-center justify-between p-6 bg-blue-600 text-white rounded-2xl shadow-xl hover:bg-blue-700 transition-all group">
              <div className="flex items-center gap-4">
                <FileText className="h-6 w-6" />
                <span className="font-bold">Submit Paper</span>
              </div>
              <ChevronRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            
            <Link href="/admin/manuscripts" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-blue-500 transition-all group">
              <div className="flex items-center gap-4">
                <Settings className="h-6 w-6 text-slate-400" />
                <span className="font-bold">Editorial Admin</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link href="/finance" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-green-500 transition-all group">
              <div className="flex items-center gap-4">
                <DollarSign className="h-6 w-6 text-slate-400" />
                <span className="font-bold">Finance</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link href="/admin/eic-approval" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-purple-500 transition-all group">
              <div className="flex items-center gap-4">
                <ShieldCheck className="h-6 w-6 text-slate-400" />
                <span className="font-bold">EIC Gate</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>

        <JournalCarousel />
        <HomeDiscoveryBlocks />
        <LatestArticles />

        {/* Branding Footer Section */}
        <section className="py-20 border-t border-slate-100">
          <div className="mx-auto max-w-7xl px-4 text-center">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-[0.3em] mb-12">Trusted by Global Institutions</h3>
            <div className="flex flex-wrap justify-center gap-12 grayscale opacity-40">
              {/* 这里模拟合作伙伴 Logo */}
              <div className="text-2xl font-serif font-black italic">UNIVERSITY PRESS</div>
              <div className="text-2xl font-serif font-black italic">GLOBAL SCIENCE</div>
              <div className="text-2xl font-serif font-black italic">RESEARCH HUB</div>
              <div className="text-2xl font-serif font-black italic">ACADEMIC NETWORK</div>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-900 text-slate-400 py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-12 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="font-serif text-2xl font-bold text-white mb-6">ScholarFlow</div>
            <p className="text-sm leading-relaxed">Leading the transition to open science by providing a seamless, AI-enhanced publishing experience.</p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">Journals</h4>
            <ul className="space-y-4 text-sm">
              <li className="hover:text-white cursor-pointer">Medicine</li>
              <li className="hover:text-white cursor-pointer">Engineering</li>
              <li className="hover:text-white cursor-pointer">Humanities</li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">Resources</h4>
            <ul className="space-y-4 text-sm">
              <li className="hover:text-white cursor-pointer">Author Guidelines</li>
              <li className="hover:text-white cursor-pointer">Editorial Policies</li>
              <li className="hover:text-white cursor-pointer">Open Access</li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white mb-6 uppercase text-xs tracking-widest">Connect</h4>
            <ul className="space-y-4 text-sm">
              <li className="hover:text-white cursor-pointer">Twitter / X</li>
              <li className="hover:text-white cursor-pointer">LinkedIn</li>
              <li className="hover:text-white cursor-pointer">Support</li>
            </ul>
          </div>
        </div>
        <div className="mx-auto max-w-7xl px-4 border-t border-slate-800 pt-8 text-center text-xs">
          <p>&copy; 2026 ScholarFlow Publishing. All rights reserved. Registered in Arch Linux.</p>
        </div>
      </footer>
    </div>
  )
}
