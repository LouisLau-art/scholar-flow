'use client'

import { useState } from 'react'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { ApiClient } from '@/lib/api-client'

export default function SubmissionForm() {
  /**
   * 投稿表单组件 (Client Component)
   * 包含 AI 解析展示与手动回退逻辑
   */
  const [isUploading, setIsUploading] = useState(false)
  const [metadata, setMetadata] = useState({ title: '', abstract: '', authors: [] as string[] })

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      // 模拟调用后端 Upload API (实际路由需对应 FastAPI 地址)
      // 此处逻辑显性化：上传 -> 获取 AI 结果 -> 更新状态
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/v1/manuscripts/upload', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()

      if (result.success) {
        setMetadata(result.data)
      }
    } catch (error) {
      console.error('Upload failed:', error)
      alert('AI 解析失败，请手动填写表单信息')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* 文件上传区域 */}
      <div className="relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 p-12 transition-colors hover:border-blue-500">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={isUploading}
        />
        <Upload className="mb-4 h-12 w-12 text-slate-400" />
        <p className="text-lg font-medium text-slate-700">
          {isUploading ? 'AI is parsing your PDF...' : 'Drag and drop your PDF here'}
        </p>
        {isUploading && <Loader2 className="mt-2 h-6 w-6 animate-spin text-blue-600" />}
      </div>

      {/* 元数据展示/编辑区域 */}
      <div className="grid grid-cols-1 gap-6">
        <div>
          <label className="block text-sm font-semibold text-slate-900">Manuscript Title</label>
          <input
            type="text"
            value={metadata.title}
            onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
            placeholder="Parsed title will appear here..."
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900">Abstract</label>
          <textarea
            rows={6}
            value={metadata.abstract}
            onChange={(e) => setMetadata({ ...metadata, abstract: e.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
            placeholder="Parsed abstract will appear here..."
          />
        </div>
      </div>

      <button
        disabled={!metadata.title || isUploading}
        className="w-full rounded-md bg-blue-600 py-3 text-white transition-opacity hover:bg-blue-700 disabled:opacity-50"
      >
        Finalize Submission
      </button>
    </div>
  )
}
