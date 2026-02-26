'use client'

import { useState, useEffect } from 'react'
import { Upload, Loader2, ArrowLeft } from 'lucide-react'
import { toast } from "sonner"
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { authService } from '@/services/auth'
import { supabase } from '@/lib/supabase'
import LoginPrompt from '@/components/LoginPrompt'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import type { Journal } from '@/types/journal'

const STORAGE_UPLOAD_TIMEOUT_MS = 90_000
const COVER_LETTER_UPLOAD_TIMEOUT_MS = 60_000
const METADATA_PARSE_TIMEOUT_MS = 25_000
const METADATA_PARSE_TOTAL_TIMEOUT_MS = 35_000
const DIRECT_API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL || '').trim().replace(/\/$/, '')

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`${label} timeout after ${Math.round(ms / 1000)}s`))
    }, ms)
    promise.then(
      (value) => {
        window.clearTimeout(timer)
        resolve(value)
      },
      (error) => {
        window.clearTimeout(timer)
        reject(error)
      }
    )
  })
}

function getUploadParseEndpoints(): string[] {
  const candidates = [
    DIRECT_API_ORIGIN ? `${DIRECT_API_ORIGIN}/api/v1/manuscripts/upload` : '',
    '/api/v1/manuscripts/upload',
  ].filter(Boolean)
  return Array.from(new Set(candidates))
}

function isAbortLikeError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === 'AbortError') return true
  const text = String((error as any)?.name || '') + ' ' + String((error as any)?.message || '')
  return /abort/i.test(text)
}

function isSupportedCoverLetter(file: File): boolean {
  const name = String(file.name || '').toLowerCase()
  return name.endsWith('.pdf') || name.endsWith('.doc') || name.endsWith('.docx')
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_')
}

type MetadataParsePayload = {
  response: Response
  raw: string
  result: any
  traceId: string
}

async function parseManuscriptMetadataWithFallback(file: File): Promise<MetadataParsePayload> {
  let response: Response | null = null
  let raw = ''
  let result: any = null
  let lastError: Error | null = null
  let traceId = ''

  const parseEndpoints = getUploadParseEndpoints()
  const parseStartedAt = Date.now()
  for (let idx = 0; idx < parseEndpoints.length; idx += 1) {
    if (Date.now() - parseStartedAt > METADATA_PARSE_TOTAL_TIMEOUT_MS) {
      lastError = new Error(`Metadata parsing timeout after ${Math.round(METADATA_PARSE_TOTAL_TIMEOUT_MS / 1000)}s`)
      break
    }
    const endpoint = parseEndpoints[idx]
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), METADATA_PARSE_TIMEOUT_MS)
    try {
      const formData = new FormData()
      formData.append('file', file)
      response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })
      raw = await response.text()
      try {
        result = raw ? JSON.parse(raw) : null
      } catch {
        result = null
      }
      traceId = String(result?.trace_id || '')

      if (!response.ok && response.status < 500) {
        break
      }
      if (response.ok) {
        break
      }
      lastError = new Error(
        result?.message ||
          result?.detail ||
          `Metadata parsing failed (${response.status})`
      )
    } catch (error) {
      if (isAbortLikeError(error)) {
        lastError = new Error(`Metadata parsing timeout after ${Math.round(METADATA_PARSE_TIMEOUT_MS / 1000)}s`)
        break
      }
      lastError = error instanceof Error ? error : new Error('Metadata parsing failed')
    } finally {
      window.clearTimeout(timer)
    }

    if (idx < parseEndpoints.length - 1) {
      console.warn(`[Submission] parse endpoint failed, fallback to next: ${endpoint}`)
    }
  }

  if (!response) {
    throw (lastError || new Error('AI parsing failed'))
  }

  return { response, raw, result, traceId }
}

function extractTraceId(error: unknown): string {
  try {
    if (typeof (error as any)?.trace_id === 'string' && (error as any).trace_id) {
      return String((error as any).trace_id)
    }
  } catch {}
  return ''
}

export default function SubmissionForm() {
  const router = useRouter()
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [metadata, setMetadata] = useState({ title: '', abstract: '', authors: [] as string[] })
  const [file, setFile] = useState<File | null>(null)
  const [uploadedPath, setUploadedPath] = useState<string | null>(null)
  const [coverLetterFile, setCoverLetterFile] = useState<File | null>(null)
  const [coverLetterPath, setCoverLetterPath] = useState<string | null>(null)
  const [isUploadingCoverLetter, setIsUploadingCoverLetter] = useState(false)
  const [coverLetterUploadError, setCoverLetterUploadError] = useState<string | null>(null)
  const [user, setUser] = useState<any>(null)
  const [journals, setJournals] = useState<Journal[]>([])
  const [isLoadingJournals, setIsLoadingJournals] = useState(false)
  const [journalLoadError, setJournalLoadError] = useState<string | null>(null)
  const [journalId, setJournalId] = useState('')
  const [touched, setTouched] = useState({
    title: false,
    abstract: false,
    datasetUrl: false,
    sourceCodeUrl: false,
    journal: false,
  })
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
  const journalRequired = journals.length > 0
  const journalValid = !journalRequired || journalId.trim().length > 0
  const datasetUrlValid = datasetValue === '' || isHttpUrl(datasetValue)
  const sourceCodeUrlValid = sourceCodeValue === '' || isHttpUrl(sourceCodeValue)
  const showTitleError = touched.title && !titleValid
  const showAbstractError = touched.abstract && !abstractValid
  const showDatasetError = touched.datasetUrl && !datasetUrlValid
  const showSourceCodeError = touched.sourceCodeUrl && !sourceCodeUrlValid
  const showJournalError = touched.journal && !journalValid

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

  useEffect(() => {
    let cancelled = false

    const loadJournals = async () => {
      setIsLoadingJournals(true)
      setJournalLoadError(null)
      try {
        const response = await fetch('/api/v1/public/journals')
        const payload = await response.json().catch(() => null)
        if (!response.ok || !payload?.success) {
          throw new Error(payload?.detail || payload?.message || 'Failed to load journals')
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        if (!cancelled) {
          setJournals(rows)
          if (rows.length === 1) {
            setJournalId(String(rows[0]?.id || ''))
          }
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Failed to load journals'
          setJournalLoadError(message)
        }
      } finally {
        if (!cancelled) {
          setIsLoadingJournals(false)
        }
      }
    }

    loadJournals()
    return () => {
      cancelled = true
    }
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
      const { error: uploadError } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: 'application/pdf',
            upsert: false,
          }),
        STORAGE_UPLOAD_TIMEOUT_MS,
        'Storage upload'
      )
      if (uploadError) {
        throw new Error(`Upload failed: ${uploadError.message}`)
      }
      setUploadedPath(uploadPath)
      toast.loading('File uploaded. Extracting metadata...', { id: toastId })

      const { response, raw, result, traceId: parseTraceId } = await parseManuscriptMetadataWithFallback(selectedFile)

      if (!response.ok) {
        const msg =
          result?.message ||
          result?.detail ||
          (raw && raw.length < 500 ? raw : '') ||
          'AI parsing failed'
        const err: any = new Error(msg)
        if (parseTraceId) err.trace_id = parseTraceId
        throw err
      }

      if (!result) {
        const err: any = new Error('AI parsing failed: invalid response')
        if (parseTraceId) err.trace_id = parseTraceId
        throw err
      }

      if (result.success) {
        setMetadata(result.data)
        if (result.message) {
          const info = parseTraceId ? `${result.message}（trace: ${parseTraceId}）` : result.message
          toast.success(info, { id: toastId })
        } else {
          const info = parseTraceId ? `AI parsing successful!（trace: ${parseTraceId}）` : 'AI parsing successful!'
          toast.success(info, { id: toastId })
        }
      } else {
        const err: any = new Error(result.message || "AI parsing failed")
        if (parseTraceId) err.trace_id = parseTraceId
        throw err
      }
    } catch (error) {
      console.error('Parsing failed:', error)
      const lowered = String((error as any)?.message || '').toLowerCase()
      const message =
        (error instanceof DOMException && error.name === 'AbortError') || lowered.includes('timeout')
          ? '解析超时（>25s），已跳过 AI 预填，请手动填写标题与摘要。'
          : error instanceof Error
            ? error.message
            : "AI parsing failed"
      const traceInError = extractTraceId(error)
      const finalMessage = traceInError ? `${message}（trace: ${traceInError}）` : message
      toast.error(finalMessage, { id: toastId })
      if (message.toLowerCase().includes('upload failed')) {
        setUploadError(message.replace('Upload failed: ', ''))
      } else {
        setParseError(finalMessage)
      }
    } finally {
      setIsUploading(false)
    }
  }

  const handleCoverLetterUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) {
      setCoverLetterFile(null)
      setCoverLetterPath(null)
      setCoverLetterUploadError(null)
      return
    }

    if (!isSupportedCoverLetter(selectedFile)) {
      setCoverLetterFile(null)
      setCoverLetterPath(null)
      setCoverLetterUploadError(null)
      e.currentTarget.value = ''
      toast.error('Cover letter only supports .pdf/.doc/.docx files.')
      return
    }

    if (!user) {
      toast.error('Please log in to upload a cover letter.')
      return
    }

    setCoverLetterFile(selectedFile)
    setCoverLetterPath(null)
    setCoverLetterUploadError(null)
    setIsUploadingCoverLetter(true)
    const toastId = toast.loading('Uploading cover letter...')

    try {
      const safeName = sanitizeFilename(selectedFile.name || 'cover_letter')
      const uploadPath = `${user.id}/cover-letters/${crypto.randomUUID()}_${safeName}`
      const { error: uploadError } = await withTimeout(
        supabase.storage
          .from('manuscripts')
          .upload(uploadPath, selectedFile, {
            contentType: selectedFile.type || 'application/octet-stream',
            upsert: false,
          }),
        COVER_LETTER_UPLOAD_TIMEOUT_MS,
        'Cover letter upload'
      )
      if (uploadError) {
        throw new Error(`Upload failed: ${uploadError.message}`)
      }

      setCoverLetterPath(uploadPath)
      toast.success('Cover letter uploaded.', { id: toastId })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cover letter upload failed.'
      setCoverLetterUploadError(message.replace('Upload failed: ', ''))
      toast.error(message, { id: toastId })
    } finally {
      setIsUploadingCoverLetter(false)
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
    if (isLoadingJournals) {
      toast.error('Journal list is still loading. Please wait a moment.')
      return
    }
    if (!journalValid) {
      toast.error('Please select a target journal before finalizing submission.')
      return
    }
    if (journals.length === 0) {
      toast.error('No active journals available. Please contact admin.')
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
          cover_letter_path: coverLetterPath,
          cover_letter_filename: coverLetterFile?.name || null,
          cover_letter_content_type: coverLetterFile?.type || null,
          dataset_url: datasetValue || null,
          source_code_url: sourceCodeValue || null,
          journal_id: journalId || null,
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
        <Link href="/" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
        </Link>
      </div>

      {/* 文件上传区域 */}
      <div className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
        file ? 'border-primary bg-primary/10' : 'border-border/80 hover:border-primary'
      }`}>
        <Input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileUpload}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          disabled={isUploading}
          data-testid="submission-file"
        />
        <Upload className={`mb-4 h-12 w-12 ${file ? 'text-primary' : 'text-muted-foreground'}`} />
        <p className="text-lg font-medium text-foreground">
          {file ? file.name : 'Drag and drop your PDF here'}
        </p>
        {isUploading && <Loader2 className="mt-2 h-6 w-6 animate-spin text-primary" />}
      </div>

      {/* Cover Letter 上传区域（可选） */}
      <div className="rounded-lg border border-border bg-card p-5">
        <label htmlFor="submission-cover-letter-file" className="block text-sm font-semibold text-foreground mb-2">Cover Letter (Optional)</label>
        <Input
          id="submission-cover-letter-file"
          type="file"
          accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleCoverLetterUpload}
          disabled={isUploadingCoverLetter}
          data-testid="submission-cover-letter-file"
          className="block w-full rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-muted file:px-3 file:py-1 file:text-sm file:font-medium file:text-foreground hover:file:bg-muted/70"
        />
        <div className="mt-2 text-xs text-muted-foreground">
          Accepted formats: `.pdf`, `.doc`, `.docx`.
        </div>
        {isUploadingCoverLetter && (
          <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Uploading cover letter...
          </div>
        )}
        {!isUploadingCoverLetter && coverLetterPath && (
          <InlineNotice tone="info" size="sm" className="mt-2">
            Cover letter uploaded: {coverLetterFile?.name || 'file'}
          </InlineNotice>
        )}
        {coverLetterUploadError && (
          <InlineNotice tone="danger" size="sm" className="mt-2">
            Cover letter upload failed: {coverLetterUploadError}
          </InlineNotice>
        )}
      </div>

      {/* 元数据展示/编辑区域 */}
      <div className="grid grid-cols-1 gap-6">
        <div>
          <label htmlFor="submission-journal-select" className="mb-2 block text-sm font-semibold text-foreground">Target Journal</label>
          <Select
            value={journalId}
            onValueChange={(value) => {
              setJournalId(value)
              if (!touched.journal) setTouched((prev) => ({ ...prev, journal: true }))
            }}
            disabled={isLoadingJournals || journals.length === 0}
          >
            <SelectTrigger
              id="submission-journal-select"
              className="w-full border-border/80 text-foreground"
              data-testid="submission-journal-select"
              onBlur={() => setTouched((prev) => ({ ...prev, journal: true }))}
            >
              <SelectValue
                placeholder={
                  isLoadingJournals
                    ? 'Loading journals...'
                    : journals.length === 0
                      ? 'No active journal available'
                      : 'Select a journal'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {journals.map((journal) => (
                <SelectItem key={journal.id} value={journal.id}>
                  {journal.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {showJournalError && (
            <InlineNotice tone="danger" size="sm" className="mt-2" data-testid="submission-journal-error">
              Please select a target journal.
            </InlineNotice>
          )}
          {journalLoadError && (
            <InlineNotice tone="warning" size="sm" className="mt-2">
              Journal list load failed: {journalLoadError}
            </InlineNotice>
          )}
          {!isLoadingJournals && journals.length === 0 && !journalLoadError && (
            <InlineNotice tone="warning" size="sm" className="mt-2">
              No active journal found. Please ask admin to configure journals first.
            </InlineNotice>
          )}
        </div>

        <div>
          <label htmlFor="submission-title" className="block text-sm font-semibold text-foreground mb-2">Manuscript Title</label>
          <Input
            id="submission-title"
            type="text"
            value={metadata.title}
            onChange={(e) => {
              setMetadata(prev => ({ ...prev, title: e.target.value }))
              if (!touched.title) setTouched(prev => ({ ...prev, title: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, title: true }))}
            className="w-full rounded-md border border-border/80 bg-card px-4 py-2 text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
            placeholder="Parsed title will appear here..."
            data-testid="submission-title"
          />
          {showTitleError && (
            <p className="mt-2 text-xs text-destructive" data-testid="submission-title-error">
              Title must be at least 5 characters.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="submission-abstract" className="block text-sm font-semibold text-foreground mb-2">Abstract</label>
          <Textarea
            id="submission-abstract"
            rows={6}
            value={metadata.abstract}
            onChange={(e) => {
              setMetadata(prev => ({ ...prev, abstract: e.target.value }))
              if (!touched.abstract) setTouched(prev => ({ ...prev, abstract: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, abstract: true }))}
            className="w-full rounded-md border border-border/80 bg-card px-4 py-2 text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
            placeholder="Parsed abstract will appear here..."
            data-testid="submission-abstract"
          />
          {showAbstractError && (
            <p className="mt-2 text-xs text-destructive" data-testid="submission-abstract-error">
              Abstract must be at least 30 characters.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="submission-dataset-url" className="block text-sm font-semibold text-foreground mb-2">Dataset URL (Optional)</label>
          <Input
            id="submission-dataset-url"
            type="url"
            value={datasetUrl}
            onChange={(e) => {
              setDatasetUrl(e.target.value)
              if (!touched.datasetUrl) setTouched(prev => ({ ...prev, datasetUrl: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, datasetUrl: true }))}
            className="w-full rounded-md border border-border/80 bg-card px-4 py-2 text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
            placeholder="https://example.com/dataset"
            data-testid="submission-dataset-url"
          />
          {showDatasetError && (
            <p className="mt-2 text-xs text-destructive" data-testid="submission-dataset-url-error">
              Dataset URL must start with http:// or https://.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="submission-source-url" className="block text-sm font-semibold text-foreground mb-2">Source Code URL (Optional)</label>
          <Input
            id="submission-source-url"
            type="url"
            value={sourceCodeUrl}
            onChange={(e) => {
              setSourceCodeUrl(e.target.value)
              if (!touched.sourceCodeUrl) setTouched(prev => ({ ...prev, sourceCodeUrl: true }))
            }}
            onBlur={() => setTouched(prev => ({ ...prev, sourceCodeUrl: true }))}
            className="w-full rounded-md border border-border/80 bg-card px-4 py-2 text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary focus:outline-none"
            placeholder="https://github.com/org/repo"
            data-testid="submission-source-url"
          />
          {showSourceCodeError && (
            <p className="mt-2 text-xs text-destructive" data-testid="submission-source-url-error">
              Source code URL must start with http:// or https://.
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {!user && <LoginPrompt />}
        {uploadError && (
          <InlineNotice tone="danger" size="sm">
            Upload failed: {uploadError}
          </InlineNotice>
        )}
        {parseError && (
          <InlineNotice tone="warning" size="sm">
            Parsing failed: {parseError}
          </InlineNotice>
        )}
        <Button
          onClick={handleFinalize}
          disabled={
            !fileValid ||
            !titleValid ||
            !abstractValid ||
            !journalValid ||
            !datasetUrlValid ||
            !sourceCodeUrlValid ||
            isLoadingJournals ||
            isUploading ||
            isUploadingCoverLetter ||
            isSubmitting ||
            !user
          }
          className="w-full rounded-md bg-foreground py-3 text-white font-semibold shadow-md hover:bg-foreground/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          data-testid="submission-finalize"
        >
          {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : 'Finalize Submission'}
        </Button>
        {user && (!fileValid || !titleValid || !abstractValid || !journalValid || !datasetUrlValid || !sourceCodeUrlValid) && (
          <p className="text-xs text-muted-foreground text-center" data-testid="submission-validation-hint">
            Upload a PDF, choose a journal, add a title (at least 5 chars) and abstract (at least 30 chars). Optional URLs must start with http(s).
          </p>
        )}
        {user && (
          <p className="text-xs text-muted-foreground text-center" data-testid="submission-user">
            Logged in as: {user.email}
          </p>
        )}
      </div>
    </div>
  )
}
