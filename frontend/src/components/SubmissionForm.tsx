'use client'

import { useState, useEffect } from 'react'
import { Upload, Loader2, ArrowLeft } from 'lucide-react'
import { toast } from "sonner"
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authService } from '@/services/auth'
import { supabase } from '@/lib/supabase'
import LoginPrompt from '@/components/LoginPrompt'

export default function SubmissionForm() {
  const router = useRouter()
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [metadata, setMetadata] = useState({ title: '', abstract: '', authors: [] as string[] })
  const [file, setFile] = useState<File | null>(null)
  const [uploadedPath, setUploadedPath] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const [touched, setTouched] = useState({ title: false, abstract: false, datasetUrl: false, sourceCodeUrl: false })
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [datasetUrl, setDatasetUrl] = useState('')
  const [sourceCodeUrl, setSourceCodeUrl] = useState('')
  const titleValid = metadata.title.trim().length >= 5
  const abstractValid = metadata.abstract.trim().length >= 30
  const fileValid = !!uploadedPath
  const datasetValue = datasetUrl.trim()
  const sourceCodeValue = sourceCodeUrl.trim()
  const isHttpUrl = (value: string) => value.startsWith('http://') || value.startsWith('https://')
  const datasetUrlValid = datasetValue === '' || isHttpUrl(datasetValue)
  const sourceCodeUrlValid = sourceCodeValue === '' || isHttpUrl(sourceCodeValue)
  const showTitleError = touched.title && !titleValid
  const showAbstractError = touched.abstract && !abstractValid
  const showDatasetError = touched.datasetUrl && !datasetUrlValid
  const showSourceCodeError = touched.sourceCodeUrl && !sourceCodeUrlValid

  // 检查用户登录状态
  useEffect(() => {
    const checkUser = async () => {
      const session = await authService.getSession()
      if (session?.user) {
        setUser(session.user)
      } else {
        toast.error("Please log in to submit a manuscript")
        // 重定向到登录页面或显示登录提示
      }
    }
    checkUser()

    // 监听认证状态变化
    const { data: { subscription } } = authService.onAuthStateChange((session) => {
      setUser(session?.user || null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return
    const isPdf = selectedFile.type === 'application/pdf' || selectedFile.name.toLowerCase().endsWith('.pdf')
    if (!isPdf) {
      setFile(null)
      setUploadedPath(null)
      setUploadError(null)
      setParseError(null)
      e.currentTarget.value = ''
      toast.error('Only PDF files are supported.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload a manuscript.')
      return
    }

    setFile(selectedFile)
    setUploadedPath(null)
    setUploadError(null)
    setParseError(null)
    setIsUploading(true)
    const toastId = toast.loading("Uploading and analyzing manuscript...")

    try {
      const uploadPath = `${user.id}/${crypto.randomUUID()}.pdf`
      const { error: uploadError } = await supabase.storage
        .from('manuscripts')
        .upload(uploadPath, selectedFile, {
          contentType: 'application/pdf',
          upsert: false,
        })
      if (uploadError) {
        throw new Error(`Upload failed: ${uploadError.message}`)
      }
      setUploadedPath(uploadPath)

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
        throw new Error(result.message || "AI parsing failed")
      }
    } catch (error) {
      console.error('Parsing failed:', error)
      const message = error instanceof Error ? error.message : "AI parsing failed"
      toast.error(message, { id: toastId })
      if (message.toLowerCase().includes('upload failed')) {
        setUploadError(message.replace('Upload failed: ', ''))
      } else {
        setParseError(message)
      }
    } finally {
      setIsUploading(false)
    }
  }

  const handleFinalize = async () => {
    if (!file) {
      toast.error('Please select a PDF file before submitting.')
      return
    }
    if (!uploadedPath) {
      toast.error('File upload is incomplete. Please try again.')
      return
    }
    if (!titleValid) {
      toast.error('Title must be at least 5 characters.')
      return
    }
    if (!abstractValid) {
      toast.error('Abstract must be at least 30 characters.')
      return
    }
    if (!datasetUrlValid) {
      toast.error('Dataset URL must start with http:// or https://.')
      return
    }
    if (!sourceCodeUrlValid) {
      toast.error('Source code URL must start with http:// or https://.')
      return
    }

    // 检查用户是否登录
    if (!user) {
      toast.error("Please log in to submit a manuscript")
      return
    }

    setIsSubmitting(true)
    const toastId = toast.loading("Saving manuscript to database...")

    try {
      // 获取用户的 JWT token
      const accessToken = await authService.getAccessToken()
      if (!accessToken) {
        throw new Error("No authentication token available")
      }

      // 真实调用后端保存接口
      const response = await fetch('/api/v1/manuscripts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`  // 添加 JWT token
        },
        body: JSON.stringify({
          title: metadata.title,
          abstract: metadata.abstract,
          author_id: user.id,  // 使用真实的用户 ID
          file_path: uploadedPath,
          dataset_url: datasetValue || null,
          source_code_url: sourceCodeValue || null
        }),
      })
      const result = await response.json()

      if (result.success) {
        toast.success("Manuscript submitted successfully!", { id: toastId })
        router.push('/dashboard')
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
          accept=".pdf,application/pdf"
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
            onChange={(e) => {
              setMetadata(prev => ({ ...prev, title: e.target.value }))
              if (!touched.title) setTouched(prev => ({ ...prev, title: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, title: true }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Parsed title will appear here..."
            data-testid="submission-title"
          />
          {showTitleError && (
            <p className="mt-2 text-xs text-red-600" data-testid="submission-title-error">
              Title must be at least 5 characters.
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">Abstract</label>
          <textarea
            rows={6}
            value={metadata.abstract}
            onChange={(e) => {
              setMetadata(prev => ({ ...prev, abstract: e.target.value }))
              if (!touched.abstract) setTouched(prev => ({ ...prev, abstract: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, abstract: true }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Parsed abstract will appear here..."
            data-testid="submission-abstract"
          />
          {showAbstractError && (
            <p className="mt-2 text-xs text-red-600" data-testid="submission-abstract-error">
              Abstract must be at least 30 characters.
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">Dataset URL (Optional)</label>
          <input
            type="url"
            value={datasetUrl}
            onChange={(e) => {
              setDatasetUrl(e.target.value)
              if (!touched.datasetUrl) setTouched(prev => ({ ...prev, datasetUrl: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, datasetUrl: true }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="https://example.com/dataset"
            data-testid="submission-dataset-url"
          />
          {showDatasetError && (
            <p className="mt-2 text-xs text-red-600" data-testid="submission-dataset-url-error">
              Dataset URL must start with http:// or https://.
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">Source Code URL (Optional)</label>
          <input
            type="url"
            value={sourceCodeUrl}
            onChange={(e) => {
              setSourceCodeUrl(e.target.value)
              if (!touched.sourceCodeUrl) setTouched(prev => ({ ...prev, sourceCodeUrl: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, sourceCodeUrl: true }))}
            className="w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="https://github.com/org/repo"
            data-testid="submission-source-url"
          />
          {showSourceCodeError && (
            <p className="mt-2 text-xs text-red-600" data-testid="submission-source-url-error">
              Source code URL must start with http:// or https://.
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {!user && <LoginPrompt />}
        {uploadError && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            Upload failed: {uploadError}
          </div>
        )}
        {parseError && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Parsing failed: {parseError}
          </div>
        )}
        <button
          onClick={handleFinalize}
          disabled={!fileValid || !titleValid || !abstractValid || !datasetUrlValid || !sourceCodeUrlValid || isUploading || isSubmitting || !user}
          className="w-full rounded-md bg-slate-900 py-3 text-white font-semibold shadow-md hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          data-testid="submission-finalize"
        >
          {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : 'Finalize Submission'}
        </button>
        {user && (!fileValid || !titleValid || !abstractValid || !datasetUrlValid || !sourceCodeUrlValid) && (
          <p className="text-xs text-slate-500 text-center" data-testid="submission-validation-hint">
            Upload a PDF, add a title (≥5 chars) and an abstract (≥30 chars). Optional URLs must start with http(s).
          </p>
        )}
        {user && (
          <p className="text-xs text-slate-500 text-center" data-testid="submission-user">
            Logged in as: {user.email}
          </p>
        )}
      </div>
    </div>
  )
}
