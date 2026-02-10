'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { authService } from '@/services/auth'
import SiteHeader from '@/components/layout/SiteHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import TiptapEditor from '@/components/cms/TiptapEditor'
import { Loader2, Upload, FileText, AlertCircle, ArrowLeft, CheckCircle2 } from 'lucide-react'
import Link from 'next/link'
import { compressImage } from '@/lib/image-utils'

export default function SubmitRevisionPage() {
  const params = useParams()
  const router = useRouter()
  const manuscriptId = String((params as Record<string, string | string[]> | null)?.id || '')
  
  const [manuscript, setManuscript] = useState<any>(null)
  const [revisionRequest, setRevisionRequest] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const [responseLetter, setResponseLetter] = useState('')
  const [file, setFile] = useState<File | null>(null)
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
    if (!file) {
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
       formData.append('file', file)
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
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-8">
        <div className="mb-6">
          <Link href="/dashboard" className="text-sm text-slate-500 hover:text-slate-900 flex items-center gap-1 mb-4">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-slate-900">Submit Revision</h1>
          <p className="text-slate-600 mt-2">
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
               <CardDescription>Upload your revised manuscript and provide a response to the reviewers.</CardDescription>
             </CardHeader>
             <CardContent className="space-y-8">
               
               {/* File Upload */}
               <div className="space-y-3">
                 <Label className="text-base">Revised Manuscript (PDF)</Label>
                 <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors">
                   <input 
                     type="file" 
                     accept="application/pdf"
                     onChange={(e) => setFile(e.target.files?.[0] || null)}
                     className="hidden" 
                     id="file-upload"
                   />
                   <label htmlFor="file-upload" className="cursor-pointer block">
                     {file ? (
                       <div className="flex flex-col items-center gap-2 text-emerald-600">
                         <CheckCircle2 className="h-10 w-10" />
                         <span className="font-semibold text-lg">{file.name}</span>
                         <span className="text-sm text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                         <Button variant="outline" size="sm" className="mt-2" onClick={(e) => {
                           e.preventDefault()
                           setFile(null)
                         }}>Remove</Button>
                       </div>
                     ) : (
                       <div className="flex flex-col items-center gap-2 text-slate-500">
                         <Upload className="h-10 w-10" />
                         <span className="font-semibold text-lg">Click to upload PDF</span>
                         <span className="text-sm">or drag and drop</span>
                       </div>
                     )}
                   </label>
                 </div>
               </div>
               
               {/* Response Letter */}
               <div className="space-y-3">
                 <Label className="text-base">Response Letter</Label>
	                 <p className="text-sm text-slate-500">
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
                   disabled={isSubmitting || !file || !responseLetter}
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
