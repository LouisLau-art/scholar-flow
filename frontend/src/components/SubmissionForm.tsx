'use client'

import { useState, useEffect } from 'react'
import { Upload, Loader2, ArrowLeft } from 'lucide-react'
import { toast } from "sonner"
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

export default function SubmissionForm() {
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [metadata, setMetadata] = useState({ title: '', abstract: '', authors: [] as string[] })
  const [file, setFile] = useState<File | null>(null)
  const [user, setUser] = useState<any>(null)

  // 检查用户登录状态
  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.user) {
        setUser(session.user)
      } else {
        toast.error("Please log in to submit a manuscript")
        // 重定向到登录页面或显示登录提示
      }
    }
    checkUser()

    // 监听认证状态变化
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user || null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    setFile(selectedFile)
    setIsUploading(true)
    const toastId = toast.loading("Analyzing manuscript...")

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch('/api/v1/manuscripts/upload', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()

      if (result.success) {
        setMetadata(result.data)
        toast.success("AI parsing successful!", { id: toastId })
      } else {
        throw new Error(result.message)
      }
    } catch (error) {
      console.error('Parsing failed:', error)
      toast.error("AI parsing failed. Please fill manually.", { id: toastId })
    } finally {
      setIsUploading(false)
    }
  }

  const handleFinalize = async () => {
    if (!metadata.title) return

    // 检查用户是否登录
    if (!user) {
      toast.error("Please log in to submit a manuscript")
      return
    }

    setIsSubmitting(true)
    const toastId = toast.loading("Saving manuscript to database...")

    try {
      // 获取用户的 JWT token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error("No authentication token available")
      }

      // 真实调用后端保存接口
      const response = await fetch('/api/v1/manuscripts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`  // 添加 JWT token
        },
        body: JSON.stringify({
          title: metadata.title,
          abstract: metadata.abstract,
          author_id: user.id  // 使用真实的用户 ID
        }),
      })
      const result = await response.json()

      if (result.success) {
        toast.success("Manuscript submitted successfully!", { id: toastId })
        window.location.href = '/'
      } else {
        throw new Error(result.message || "Persistence failed")
      }
    } catch (error) {
      console.error('Submission failed:', error)
      toast.error("Failed to save. Check database connection.", { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="mb-4">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 transition-colors">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
        </Link>
      </div>

      {/* 文件上传区域 */}
      <div className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
        file ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-500'
      }`}>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={isUploading}
          data-testid="submission-file"
        />
        <Upload className={`mb-4 h-12 w-12 ${file ? 'text-blue-500' : 'text-slate-400'}`} />
        <p className="text-lg font-medium text-slate-700">
          {file ? file.name : 'Drag and drop your PDF here'}
        </p>
        {isUploading && <Loader2 className="mt-2 h-6 w-6 animate-spin text-blue-600" />}
      </div>

      {/* 元数据展示/编辑区域 */}
      <div className="grid grid-cols-1 gap-6">
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">Manuscript Title</label>
          <input
            type="text"
            value={metadata.title}
            onChange={(e) => setMetadata(prev => ({ ...prev, title: e.target.value }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Parsed title will appear here..."
            data-testid="submission-title"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">Abstract</label>
          <textarea
            rows={6}
            value={metadata.abstract}
            onChange={(e) => setMetadata(prev => ({ ...prev, abstract: e.target.value }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Parsed abstract will appear here..."
            data-testid="submission-abstract"
          />
        </div>
      </div>

      <div className="space-y-3">
        {!user && (
          <div
            className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-yellow-800 text-sm"
            data-testid="submission-login-prompt"
          >
            ⚠️ Please log in to submit a manuscript.
            <a href="/login" className="ml-1 font-semibold underline">Login here</a>
          </div>
        )}
        <button
          onClick={handleFinalize}
          disabled={!metadata.title || isUploading || isSubmitting || !user}
          className="w-full rounded-md bg-slate-900 py-3 text-white font-semibold shadow-md hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          data-testid="submission-finalize"
        >
          {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : 'Finalize Submission'}
        </button>
        {user && (
          <p className="text-xs text-slate-500 text-center" data-testid="submission-user">
            Logged in as: {user.email}
          </p>
        )}
      </div>
    </div>
  )
}
