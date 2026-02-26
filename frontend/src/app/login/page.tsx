'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import { Globe, ArrowRight, Loader2, Mail, Lock } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    const toastId = toast.loading('Signing you in...')

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      toast.success('Welcome back to ScholarFlow!', { id: toastId })
      router.push('/')
      router.refresh()
    } catch (error: any) {
      toast.error(error.message || 'Login failed', { id: toastId })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col justify-center bg-muted/30 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="flex justify-center items-center gap-2 mb-6">
          <div className="rounded-xl bg-primary p-2 text-primary-foreground">
            <Globe className="h-8 w-8" />
          </div>
          <span className="font-serif text-3xl font-bold tracking-tight text-foreground">ScholarFlow</span>
        </Link>
        <h2 className="text-center text-2xl font-bold leading-9 tracking-tight text-foreground">
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm font-medium text-muted-foreground">
          Manage your research and peer reviews in one place.
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="border border-border bg-card px-6 py-12 shadow-2xl sm:rounded-3xl sm:px-12">
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="login-email" className="block text-sm font-bold leading-6 text-foreground">Email address</label>
              <div className="mt-2 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border-0 py-3 pl-10 shadow-sm ring-1 ring-inset ring-border placeholder:text-muted-foreground transition-all focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6"
                  placeholder="name@university.edu"
                  data-testid="login-email"
                />
              </div>
            </div>

            <div>
              <label htmlFor="login-password" className="block text-sm font-bold leading-6 text-foreground">Password</label>
              <div className="mt-2 relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border-0 py-3 pl-10 shadow-sm ring-1 ring-inset ring-border placeholder:text-muted-foreground transition-all focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6"
                  data-testid="login-password"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-3 text-sm font-bold leading-6 text-primary-foreground shadow-lg transition-all hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50"
              data-testid="login-submit"
            >
              {isLoading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Sign In'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <p className="mt-10 text-center text-sm font-medium text-muted-foreground">
            Not a member?{' '}
            <Link href="/signup" className="font-bold leading-6 text-primary hover:text-primary/90 hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
