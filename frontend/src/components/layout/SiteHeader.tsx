'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { Search, Menu, X, ChevronDown, User as UserIcon, Globe } from 'lucide-react'
import { authService } from '@/services/auth'
import { getCmsMenu } from '@/services/cms'
import { useProfile } from '@/hooks/useProfile'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'

const NotificationBell = dynamic(
  () => import('@/components/notifications/NotificationBell').then((mod) => mod.NotificationBell),
  { ssr: false }
)

export default function SiteHeader() {
  const router = useRouter()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isMegaMenuOpen, setIsMegaMenuOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // 中文注释：未登录时不触发 profile 查询，减少公共页面的重复鉴权请求。
  const { profile } = useProfile({ enabled: isAuthenticated })

  const [navLinks, setNavLinks] = useState<{ name: string; href: string; hasMega?: boolean }[]>([
    { name: 'Journals', href: '/journals', hasMega: true },
    { name: 'Topics', href: '/topics' },
    { name: 'Publish', href: '/submit' },
    { name: 'About', href: '/about' },
  ])

  useEffect(() => {
    let isMounted = true

    // 中文注释：统一通过 Supabase session 探测登录态，不再依赖 localStorage token 镜像。
    authService
      .getSession()
      .then((session) => {
        if (isMounted) setIsAuthenticated(!!session)
      })
      .catch(() => {
        if (isMounted) setIsAuthenticated(false)
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
          setNavLinks([{ name: 'Journals', href: '/journals', hasMega: true }, ...dynamic])
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

  const handleSearch = () => {
    const q = searchQuery.trim()
    setIsSearchOpen(false)
    if (!q) {
      router.push('/search')
      return
    }
    router.push(`/search?q=${encodeURIComponent(q)}`)
  }

  // Display Name: Full Name > Email > "User"
  const displayName = profile?.full_name || profile?.email || 'User'
  const displayAvatar = profile?.avatar_url

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-card/95 text-foreground shadow-xl backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-20 items-center justify-between">
          
          {/* Logo */}
          <div className="flex items-center gap-12">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="bg-primary p-1.5 rounded-lg group-hover:bg-primary/90 transition-colors">
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
                  onBlur={(event) => {
                    if (!link.hasMega) return
                    const nextTarget = event.relatedTarget as Node | null
                    if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
                      setIsMegaMenuOpen(false)
                    }
                  }}
                >
                  {link.hasMega ? (
                    <Button
                      type="button"
                      variant="ghost"
                      aria-haspopup="menu"
                      aria-expanded={isMegaMenuOpen}
                      aria-controls="site-mega-menu"
                      onClick={() => setIsMegaMenuOpen((prev) => !prev)}
                      onFocus={() => setIsMegaMenuOpen(true)}
                      onKeyDown={(event) => {
                        if (event.key === 'Escape') {
                          setIsMegaMenuOpen(false)
                        }
                      }}
                      className="flex items-center gap-1 py-8 px-0 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card"
                    >
                      {link.name}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  ) : (
                    <Link 
                      href={link.href}
                      className="flex items-center gap-1 py-8 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.name}
                    </Link>
                  )}
                </div>
              ))}
            </nav>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-6">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Search"
              onClick={() => setIsSearchOpen(true)}
              className="hidden text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card sm:inline-flex"
            >
              <Search className="h-5 w-5" />
            </Button>
            <div className="hidden h-6 w-px bg-border/60 sm:block" />

            {isAuthenticated ? <NotificationBell isAuthenticated={isAuthenticated} /> : null}

            {isAuthenticated ? (
              <div className="hidden items-center gap-3 text-sm font-semibold text-foreground sm:flex">
                <Link href="/settings" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                  <Avatar className="h-8 w-8 border border-border/70">
                    <AvatarImage src={displayAvatar || undefined} />
                    <AvatarFallback className="bg-muted text-foreground text-xs">
                      {displayName.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="max-w-40 truncate text-foreground">{displayName}</span>
                </Link>
                <Link href="/dashboard" className="text-muted-foreground transition-colors hover:text-foreground">
                  Dashboard
                </Link>
                <Link href="/settings" className="text-muted-foreground transition-colors hover:text-foreground">
                  Settings
                </Link>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleSignOut}
                  className="px-0 text-muted-foreground transition-colors hover:text-foreground"
                >
                  Sign Out
                </Button>
              </div>
            ) : (
              <Link href="/login" className="hidden items-center gap-2 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground sm:flex">
                <UserIcon className="h-4 w-4" /> Sign In
              </Link>
            )}
            
            <Link 
              href="/submit" 
              className="rounded-full bg-primary px-6 py-2.5 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20 transition-[background-color,transform,box-shadow] duration-200 hover:bg-primary/90 hover:scale-105 active:scale-95"
            >
              Submit
            </Link>

            {/* Mobile Menu Toggle */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={isMobileMenuOpen ? 'Close mobile menu' : 'Open mobile menu'}
              className="text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-card lg:hidden"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={isSearchOpen} onOpenChange={setIsSearchOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>搜索</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Label htmlFor="site-header-search-input" className="sr-only">
              Search by title, abstract, or DOI
            </Label>
            <Input
              id="site-header-search-input"
              value={searchQuery}
              placeholder="输入关键词（标题 / 摘要 / DOI）"
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch()
              }}
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsSearchOpen(false)}
              >
                取消
              </Button>
              <Button type="button" onClick={handleSearch}>
                搜索
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Mega Menu */}
      {isMegaMenuOpen && (
        <div 
          id="site-mega-menu"
          className="absolute left-0 w-full bg-card text-foreground shadow-2xl border-b border-border sf-motion-enter-top-fast"
          onMouseEnter={() => setIsMegaMenuOpen(true)}
          onMouseLeave={() => setIsMegaMenuOpen(false)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setIsMegaMenuOpen(false)
            }
          }}
        >
          {/* ... (Existing Mega Menu Content) ... */}
          <div className="mx-auto max-w-7xl px-8 py-12 grid grid-cols-4 gap-12">
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-primary border-b border-primary/20 pb-2">Medicine</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Oncology">Oncology</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Neuroscience">Neuroscience</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Public%20Health">Public Health</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-primary border-b border-primary/20 pb-2">Physical Sciences</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Physics">Physics</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Chemistry">Chemistry</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Materials">Materials</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-serif text-lg font-bold mb-4 text-primary border-b border-primary/20 pb-2">Social Sciences</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Psychology">Psychology</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Economics">Economics</Link></li>
                <li><Link className="hover:text-primary" href="/search?mode=journals&q=Education">Education</Link></li>
              </ul>
            </div>
            <div className="bg-muted/40 p-6 rounded-xl border border-border/60">
              <h4 className="font-bold mb-2">Can&apos;t find your journal?</h4>
              <p className="text-sm text-muted-foreground mb-4">Explore our full portfolio of 200+ high-impact journals.</p>
              <Link href="/journals" className="text-sm font-bold text-primary flex items-center gap-1 hover:underline">
                View all journals →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="fixed h-screen w-full space-y-4 border-t border-border/30 bg-card px-4 py-8 text-foreground sf-motion-enter-right lg:hidden">
          {navLinks.map(link => (
            <Link 
              key={link.name} 
              href={link.href}
              className="block text-xl font-bold text-foreground/90"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {link.name}
            </Link>
          ))}
          <div className="pt-8 border-t border-border/30 space-y-4">
            {isAuthenticated ? (
              <>
                <Link href="/dashboard" className="block text-muted-foreground transition-colors hover:text-foreground">Dashboard</Link>
                <Link href="/settings" className="block text-muted-foreground transition-colors hover:text-foreground">Settings</Link>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleSignOut}
                  className="block justify-start px-0 text-left text-muted-foreground"
                >
                  Sign Out
                </Button>
              </>
            ) : (
              <Link href="/login" className="block text-muted-foreground">Sign In</Link>
            )}
            <Link href="/submit" className="block text-primary font-bold text-xl">Submit your manuscript</Link>
          </div>
        </div>
      )}
    </header>
  )
}
