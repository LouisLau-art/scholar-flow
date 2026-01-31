'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import { showErrorToast } from '@/lib/utils'
import { Globe, ArrowRight, Loader2, Mail, Lock, UserPlus } from 'lucide-react'

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
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      })

      if (error) throw error

      // 中文注释:
      // - 部分环境（本地/测试）可能关闭邮箱确认，此时会直接返回 session。
      // - 若有 session，则视为“已登录”并进入 Dashboard；否则提示用户去邮箱验证。
      if (data?.session) {
        toast.success('Registration successful! Welcome to ScholarFlow.', { id: toastId })
        router.push('/dashboard')
      } else {
        toast.success('Registration successful! Please check your email for verification.', { id: toastId })
        router.push('/login')
      }
    } catch (error: any) {
      showErrorToast(error, 'Signup failed', { id: toastId })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-6">
          <div className="bg-blue-600 p-2 rounded-xl text-white">
            <UserPlus className="h-8 w-8" />
          </div>
        </div>
        <h2 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">
          Join ScholarFlow
        </h2>
        <p className="mt-2 text-sm text-slate-500 font-medium">
          Start your journey in open science publishing.
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-[480px]">
        <div className="bg-white px-6 py-12 shadow-2xl shadow-slate-200 sm:rounded-3xl sm:px-12 border border-slate-100">
          <form className="space-y-6" onSubmit={handleSignup}>
            <div>
              <label className="block text-sm font-bold text-slate-900">University Email</label>
              <div className="mt-2 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full rounded-xl border-0 py-3 pl-10 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-blue-600 sm:text-sm transition-all"
                  placeholder="name@university.edu"
                  data-testid="signup-email"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-900">Create Password</label>
              <div className="mt-2 relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-xl border-0 py-3 pl-10 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-blue-600 sm:text-sm transition-all"
                  data-testid="signup-password"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">At least 8 characters with numbers and symbols.</p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full justify-center items-center gap-2 rounded-xl bg-blue-600 px-3 py-3 text-sm font-bold leading-6 text-white shadow-lg hover:bg-blue-500 transition-all disabled:opacity-50"
              data-testid="signup-submit"
            >
              {isLoading ? <Loader2 className="animate-spin h-5 w-5" /> : 'Create Account'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-10">
            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
              <div className="relative flex justify-center text-sm font-medium leading-6">
                <span className="bg-white px-6 text-slate-400 font-bold uppercase tracking-widest text-[10px]">Already have an account?</span>
              </div>
            </div>
            <div className="mt-6">
              <Link 
                href="/login" 
                className="flex w-full justify-center rounded-xl bg-slate-50 px-3 py-3 text-sm font-bold text-slate-900 shadow-sm ring-1 ring-inset ring-slate-200 hover:bg-slate-100 transition-all"
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
