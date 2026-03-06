'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, Lock, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { supabase } from '@/lib/supabase'

export default function SetPasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (password.length < 8) {
      toast.error('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      toast.error('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      const { data } = await supabase.auth.getSession()
      if (!data.session) {
        toast.error('Your activation session has expired. Please request a new activation email.')
        router.push('/login')
        return
      }

      const { error } = await supabase.auth.updateUser({ password })
      if (error) {
        throw error
      }

      toast.success('Password updated. Redirecting to your dashboard…')
      router.push('/dashboard')
      router.refresh()
    } catch (error: any) {
      toast.error(error?.message || 'Failed to update password.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-12">
      <div className="w-full max-w-lg rounded-3xl border border-border bg-card p-8 shadow-2xl">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-bold text-foreground">Set Your Password</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Activate your reviewer account by choosing a secure password.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="new-password" className="block text-sm font-bold text-foreground">
              New password
            </label>
            <div className="relative mt-2">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="pl-10"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="confirm-password" className="block text-sm font-bold text-foreground">
              Confirm password
            </label>
            <div className="relative mt-2">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="pl-10"
                required
              />
            </div>
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full gap-2">
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Set password'}
            {!isSubmitting ? <ArrowRight className="h-4 w-4" /> : null}
          </Button>
        </form>
      </div>
    </div>
  )
}
