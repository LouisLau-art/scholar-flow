'use client'

import { useState } from 'react'
import { Upload, Loader2, ArrowLeft } from 'lucide-react'
import { toast } from "sonner"
import Link from 'next/link'

export default function SubmissionForm() {
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [metadata, setMetadata] = useState({ title: '', abstract: '', authors: [] as string[] })
  const [file, setFile] = useState<File | null>(null)

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
    setIsSubmitting(true)
    // 模拟最终提交
    await new Promise(resolve => setTimeout(resolve, 1000))
    toast.success("Manuscript submitted successfully!")
    setIsSubmitting(false)
    // 可以在这里跳转回首页
    window.location.href = '/'
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
          />
        </div>
      </div>

      <button
        onClick={handleFinalize}
        disabled={!metadata.title || isUploading || isSubmitting}
        className="w-full rounded-md bg-slate-900 py-3 text-white font-semibold shadow-md hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
      >
        {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : 'Finalize Submission'}
      </button>
    </div>
  )
}