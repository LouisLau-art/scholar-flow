'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import { Globe, ArrowRight, Loader2, Mail, Lock, UserPlus } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    const toastId = toast.loading('Creating your account...')

    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      })

      if (error) throw error

      toast.success('Registration successful! Please check your email for verification.', { id: toastId })
      router.push('/login')
    } catch (error: any) {
      toast.error(error.message || 'Signup failed', { id: toastId })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col justify-center bg-muted/30 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-6">
          <div className="rounded-xl bg-primary p-2 text-primary-foreground">
            <UserPlus className="h-8 w-8" />
          </div>
        </div>
        <h2 className="text-3xl font-serif font-bold tracking-tight text-foreground">
          Join ScholarFlow
        </h2>
        <p className="mt-2 text-sm font-medium text-muted-foreground">
          Start your journey in open science publishing.
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="border border-border bg-card px-6 py-12 shadow-2xl sm:rounded-3xl sm:px-12">
          <form className="space-y-6" onSubmit={handleSignup}>
            <div>
              <label htmlFor="signup-email" className="block text-sm font-bold text-foreground">University Email</label>
              <div className="mt-2 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border-0 py-3 pl-10 shadow-sm ring-1 ring-inset ring-border transition-all focus:ring-2 focus:ring-primary sm:text-sm"
                  placeholder="name@university.edu"
                />
              </div>
            </div>

            <div>
              <label htmlFor="signup-password" className="block text-sm font-bold text-foreground">Create Password</label>
              <div className="mt-2 relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="signup-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border-0 py-3 pl-10 shadow-sm ring-1 ring-inset ring-border transition-all focus:ring-2 focus:ring-primary sm:text-sm"
                />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">At least 8 characters with numbers and symbols.</p>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-3 text-sm font-bold leading-6 text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Create Account'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <div className="mt-10">
            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div>
              <div className="relative flex justify-center text-sm font-medium leading-6">
                <span className="bg-card px-6 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Already have an account?</span>
              </div>
            </div>
            <div className="mt-6">
              <Link 
                href="/login" 
                className="flex w-full justify-center rounded-xl bg-muted px-3 py-3 text-sm font-bold text-foreground shadow-sm ring-1 ring-inset ring-border transition-all hover:bg-muted/80"
              >
                Sign In Instead
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
