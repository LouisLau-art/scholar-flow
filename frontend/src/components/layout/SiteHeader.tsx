'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Search, Menu, X, ChevronDown, User as UserIcon, Globe } from 'lucide-react'
import { authService } from '@/services/auth'
import { NotificationBell } from '@/components/notifications/NotificationBell'
import { getCmsMenu } from '@/services/cms'
import { useProfile } from '@/hooks/useProfile'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export default function SiteHeader() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isMegaMenuOpen, setIsMegaMenuOpen] = useState(false)
  
  // Use React Query for profile data (handles caching & updates)
  const { profile } = useProfile()
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  const [navLinks, setNavLinks] = useState<{ name: string; href: string; hasMega?: boolean }[]>([
    { name: 'Journals', href: '#', hasMega: true },
    { name: 'Topics', href: '/topics' },
    { name: 'Publish', href: '/submit' },
    { name: 'About', href: '/about' },
  ])

  useEffect(() => {
    let isMounted = true
    
    // Check initial session
    authService.getSession().then(session => {
      if (isMounted) setIsAuthenticated(!!session)
    })

    // CMS Menu
    ;(async () => {
      try {
        const headerMenu = await getCmsMenu('header')
        const dynamic = (headerMenu || [])
          .map((item: any) => {
            const name = String(item?.label || '').trim()
            const href = item?.page_slug ? `/journal/${item.page_slug}` : String(item?.url || '').trim()
            if (!name || !href) return null
            return { name, href }
          })
          .filter(Boolean) as { name: string; href: string }[]

        if (isMounted && dynamic.length > 0) {
          setNavLinks([{ name: 'Journals', href: '#', hasMega: true }, ...dynamic])
        }
      } catch {
        // Ignore
      }
    })()

    const { data: { subscription } } = authService.onAuthStateChange((session) => {
      setIsAuthenticated(!!session)
    })

    return () => {
      isMounted = false
      subscription.unsubscribe()
    }
  }, [])

  const handleSignOut = async () => {
    await authService.signOut()
    window.location.href = '/' // Force reload to clear query cache
  }

  // Display Name: Full Name > Email > "User"
  const displayName = profile?.full_name || profile?.email || 'User'
  const displayAvatar = profile?.avatar_url

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-900 text-white shadow-xl">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-20 items-center justify-between">
          
          {/* Logo */}
          <div className="flex items-center gap-12">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="bg-blue-600 p-1.5 rounded-lg group-hover:bg-blue-500 transition-colors">
                <Globe className="h-6 w-6 text-white" />
              </div>
              <span className="font-serif text-2xl font-bold tracking-tight">
                ScholarFlow
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-8">
              {navLinks.map((link) => (
                <div 
                  key={link.name}
                  className="relative group"
                  onMouseEnter={() => link.hasMega && setIsMegaMenuOpen(true)}
                  onMouseLeave={() => link.hasMega && setIsMegaMenuOpen(false)}
                >
                  <Link 
                    href={link.href}
                    className="flex items-center gap-1 text-sm font-semibold text-slate-300 hover:text-white transition-colors py-8"
                  >
                    {link.name}
                    {link.hasMega && <ChevronDown className="h-4 w-4 opacity-50" />}
                  </Link>
                </div>
              ))}
            </nav>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-6">
            <button className="hidden sm:block text-slate-400 hover:text-white transition-colors">
              <Search className="h-5 w-5" />
            </button>
            <div className="h-6 w-px bg-slate-800 hidden sm:block" />

            <NotificationBell isAuthenticated={isAuthenticated} />

            {isAuthenticated ? (
              <div className="hidden sm:flex items-center gap-3 text-sm font-semibold text-slate-200">
                <Link href="/settings" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                  <Avatar className="h-8 w-8 border border-slate-700">
                    <AvatarImage src={displayAvatar || undefined} />
                    <AvatarFallback className="bg-slate-700 text-slate-200 text-xs">
                      {displayName.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="max-w-[160px] truncate text-slate-200">{displayName}</span>
                </Link>
                <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
                  Dashboard
                </Link>
                <Link href="/settings" className="text-slate-400 hover:text-white transition-colors">
                  Settings
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link href="/login" className="hidden sm:flex items-center gap-2 text-sm font-semibold text-slate-300 hover:text-white">
                <UserIcon className="h-4 w-4" /> Sign In
              </Link>
            )}
            
            <Link 
              href="/submit" 
              className="rounded-full bg-blue-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-900/20 hover:bg-blue-500 hover:scale-105 active:scale-95 transition-all"
            >
              Submit
            </Link>

            {/* Mobile Menu Toggle */}
            <button 
              className="lg:hidden text-slate-300"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mega Menu */}
      {isMegaMenuOpen && (
        <div 
          className="absolute left-0 w-full bg-white text-slate-900 shadow-2xl border-b border-slate-200 animate-in fade-in slide-in-from-top-2 duration-200"
          onMouseEnter={() => setIsMegaMenuOpen(true)}
          onMouseLeave={() => setIsMegaMenuOpen(false)}
        >
          {/* ... (Existing Mega Menu Content) ... */}
          <div className="mx-auto max-w-7xl px-8 py-12 grid grid-cols-4 gap-12">
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-blue-600 border-b border-blue-100 pb-2">Medicine</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="hover:text-blue-600 cursor-pointer">Oncology</li>
                <li className="hover:text-blue-600 cursor-pointer">Neuroscience</li>
                <li className="hover:text-blue-600 cursor-pointer">Public Health</li>
              </ul>
            </div>
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-blue-600 border-b border-blue-100 pb-2">Physical Sciences</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="hover:text-blue-600 cursor-pointer">Physics</li>
                <li className="hover:text-blue-600 cursor-pointer">Chemistry</li>
                <li className="hover:text-blue-600 cursor-pointer">Materials</li>
              </ul>
            </div>
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-blue-600 border-b border-blue-100 pb-2">Social Sciences</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="hover:text-blue-600 cursor-pointer">Psychology</li>
                <li className="hover:text-blue-600 cursor-pointer">Economics</li>
                <li className="hover:text-blue-600 cursor-pointer">Education</li>
              </ul>
            </div>
            <div className="bg-slate-50 p-6 rounded-xl border border-slate-100">
              <h4 className="font-bold mb-2">Can&apos;t find your journal?</h4>
              <p className="text-sm text-slate-500 mb-4">Explore our full portfolio of 200+ high-impact journals.</p>
              <Link href="#" className="text-sm font-bold text-blue-600 flex items-center gap-1 hover:underline">
                View all journals →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden bg-slate-900 border-t border-slate-800 px-4 py-8 space-y-4 animate-in slide-in-from-right w-full h-screen fixed">
          {navLinks.map(link => (
            <Link 
              key={link.name} 
              href={link.href}
              className="block text-xl font-bold text-slate-200"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {link.name}
            </Link>
          ))}
          <div className="pt-8 border-t border-slate-800 space-y-4">
            {isAuthenticated ? (
              <>
                <Link href="/dashboard" className="block text-slate-400">Dashboard</Link>
                <Link href="/settings" className="block text-slate-400">Settings</Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="block text-left text-slate-400"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <Link href="/login" className="block text-slate-400">Sign In</Link>
            )}
            <Link href="/submit" className="block text-blue-400 font-bold text-xl">Submit your manuscript</Link>
          </div>
        </div>
      )}
    </header>
  )
}