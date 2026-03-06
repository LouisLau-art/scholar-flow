'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { authService } from '@/services/auth'
import SiteHeader from '@/components/layout/SiteHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { InlineNotice } from '@/components/ui/inline-notice'
import { toast } from 'sonner'
import { Loader2, AlertCircle, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { compressImage } from '@/lib/image-utils'

const TiptapEditor = dynamic(() => import('@/components/cms/TiptapEditor'), {
  ssr: false,
})

export default function SubmitRevisionPage() {
  const params = useParams()
  const router = useRouter()
  const manuscriptId = String((params as Record<string, string | string[]> | null)?.id || '')
  
  const [manuscript, setManuscript] = useState<any>(null)
  const [revisionRequest, setRevisionRequest] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const [responseLetter, setResponseLetter] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [wordFile, setWordFile] = useState<File | null>(null)
  const [isEmbeddingImage, setIsEmbeddingImage] = useState(false)

  useEffect(() => {
    async function loadData() {
      try {
        const token = await authService.getAccessToken()
        if (!token) {
          router.push('/login')
          return
        }
        
        // 1. Fetch Manuscript Details（登录态，非公开文章页）
        const msRes = await fetch(`/api/v1/manuscripts/by-id/${manuscriptId}`, {
           headers: { Authorization: `Bearer ${token}` }
        })
        const msData = await msRes.json()
        if (!msData.success) throw new Error('Failed to load manuscript')
        
        const ms = msData.data
        if (!['major_revision', 'minor_revision', 'revision_requested'].includes(ms.status)) {
          toast.error('This manuscript is not awaiting revision.')
          router.push('/dashboard')
          return
        }
        setManuscript(ms)
        
        // 2. Fetch Revision History to get the request
        const verRes = await fetch(`/api/v1/manuscripts/${manuscriptId}/versions`, {
           headers: { Authorization: `Bearer ${token}` }
        })
        const verData = await verRes.json()
        let pendingRevision: any = null
        if (verData.success) {
           // Find pending revision
           const revisions = verData.data.revisions || []
           pendingRevision = revisions.find((r: any) => r.status === 'pending')
           if (pendingRevision) {
             setRevisionRequest(pendingRevision)
           }
        }
        if (!pendingRevision && ms?.author_latest_feedback_comment) {
          // 中文注释:
          // 兼容 ME/AE 预审退回（未创建 revisions 记录），作者仍应看到可执行的反馈意见。
          setRevisionRequest({
            decision_type: 'technical',
            editor_comment: ms.author_latest_feedback_comment,
            created_at: ms.author_latest_feedback_at || null,
          })
        }
        
      } catch (error) {
        console.error(error)
        toast.error('Failed to load data')
      } finally {
        setIsLoading(false)
      }
    }
    
    loadData()
  }, [manuscriptId, router])
  
  const handleSubmit = async () => {
    if (!wordFile) {
      toast.error('Please upload your revised manuscript Word file.')
      return
    }
    if (!pdfFile) {
      toast.error('Please upload your revised manuscript PDF.')
      return
    }
    if (!responseLetter || responseLetter.trim().length < 20) {
      toast.error('Please provide a detailed response letter (min 20 chars).')
      return
    }
    
    setIsSubmitting(true)
    try {
       const token = await authService.getAccessToken()
       const formData = new FormData()
       formData.append('word_file', wordFile)
       formData.append('pdf_file', pdfFile)
       formData.append('response_letter', responseLetter)
       
       const res = await fetch(`/api/v1/manuscripts/${manuscriptId}/revisions`, {
         method: 'POST',
         headers: {
           Authorization: `Bearer ${token}`,
         },
         body: formData
       })
       
       const result = await res.json()
       if (!res.ok) throw new Error(result.detail || 'Submission failed')
       
       toast.success('Revision submitted successfully!')
       router.push('/dashboard')
       
    } catch (error: any) {
      console.error(error)
      toast.error(error.message || 'Submission failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  const embedImageAsDataUrl = async (file: File): Promise<string> => {
    if (!file.type.startsWith('image/')) {
      throw new Error('请选择图片文件')
    }
    setIsEmbeddingImage(true)
    try {
      // MVP：不走后端存储，直接压缩后以 Data URL 嵌入 response letter（仅用于内部流转）
      const compressed = await compressImage(file, 1200, 1200, 0.82)
      const maxBytes = 900 * 1024 // 控制体积，避免 HTML/DB 过大
      if (compressed.size > maxBytes) {
        throw new Error('图片过大（已压缩仍 > 900KB），请裁剪后再试')
      }
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result || ''))
        reader.onerror = () => reject(new Error('读取图片失败'))
        reader.readAsDataURL(compressed)
      })
      if (!dataUrl.startsWith('data:image/')) {
        throw new Error('图片格式不支持')
      }
      return dataUrl
    } finally {
      setIsEmbeddingImage(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-muted/40 flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col font-sans">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-8">
        <div className="mb-6">
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mb-4">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Submit Revision</h1>
          <p className="text-muted-foreground mt-2">
             For manuscript: <span className="font-semibold">{manuscript?.title}</span>
          </p>
        </div>
        
        <div className="space-y-6">
           {/* Editor Comments */}
           {revisionRequest && (
             <Card className="border-amber-200 bg-amber-50">
               <CardHeader>
	                 <CardTitle className="text-amber-900 flex items-center gap-2">
	                   <AlertCircle className="h-5 w-5" />
	                   Editor&apos;s Request ({revisionRequest.decision_type} revision)
	                 </CardTitle>
               </CardHeader>
               <CardContent>
                 <div className="prose prose-sm text-amber-900">
                   <p>{revisionRequest.editor_comment}</p>
                 </div>
               </CardContent>
             </Card>
           )}
           
           {/* Submission Form */}
           <Card>
             <CardHeader>
               <CardTitle>Revision Details</CardTitle>
               <CardDescription>Upload revised Word + PDF files and provide a response to the reviewers.</CardDescription>
             </CardHeader>
             <CardContent className="space-y-6">
               <div className="rounded-lg border border-border/80 bg-card p-5">
                 <Label htmlFor="revision-word-file" className="mb-2 block text-sm font-semibold text-foreground">
                   Upload Revised Manuscript (Word) (Required)
                 </Label>
                 <Input
                   id="revision-word-file"
                   type="file"
                   accept=".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                   onChange={(e) => setWordFile(e.target.files?.[0] || null)}
                   disabled={isSubmitting}
                   className="block w-full rounded-md border border-border/80 bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
                 />
                 <div className="mt-2 text-xs text-foreground/75">Accepted formats: `.doc`, `.docx`.</div>
                 {wordFile ? (
                   <InlineNotice tone="info" size="sm" className="mt-2">
                     Word manuscript selected: {wordFile.name}
                   </InlineNotice>
                 ) : null}
               </div>

               <div className="rounded-lg border border-border/80 bg-card p-5">
                 <Label htmlFor="revision-pdf-file" className="mb-2 block text-sm font-semibold text-foreground">
                   Upload Revised Manuscript (PDF) (Required)
                 </Label>
                 <Input
                   id="revision-pdf-file"
                   type="file"
                   accept=".pdf,application/pdf"
                   onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                   disabled={isSubmitting}
                   className="block w-full rounded-md border border-border/80 bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
                 />
                 <div className="mt-2 text-xs text-foreground/75">Accepted format: `.pdf`.</div>
                 {pdfFile ? (
                   <InlineNotice tone="info" size="sm" className="mt-2">
                     Manuscript PDF selected: {pdfFile.name}
                   </InlineNotice>
                 ) : null}
               </div>
               
               {/* Response Letter */}
               <div className="space-y-3">
                 <Label className="text-base">Response Letter</Label>
	                 <p className="text-sm text-muted-foreground">
	                   Please describe the changes you have made and address the editor&apos;s comments point-by-point.
	                 </p>
               <TiptapEditor 
                   value={responseLetter}
                   onChange={setResponseLetter}
                   onUploadImage={async (img) => {
                     if (isEmbeddingImage) {
                       toast.message('图片处理中，请稍候…')
                     }
                     return await embedImageAsDataUrl(img)
                   }}
                 />
               </div>
               
               <div className="pt-4">
                 <Button 
                   size="lg" 
                   className="w-full" 
                   onClick={handleSubmit}
                   disabled={isSubmitting || !wordFile || !pdfFile || !responseLetter}
                 >
                   {isSubmitting ? (
                     <>
                       <Loader2 className="h-4 w-4 animate-spin mr-2" />
                       Submitting Revision...
                     </>
                   ) : (
                     "Submit Revision"
                   )}
                 </Button>
               </div>

             </CardContent>
           </Card>
        </div>
      </main>
    </div>
  )
}
