'use client'

import { useState, useEffect } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'

interface PDFViewerProps {
  filePath: string
}

export default function PDFViewer({ filePath }: PDFViewerProps) {
  /**
   * PDF 预览组件
   * 遵循章程：优雅降级，模块化设计
   */
  const [signedUrl, setSignedUrl] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // 模拟从 Supabase 获取签名 URL
    const fetchUrl = async () => {
      // const url = await ApiClient.getSignedUrl(filePath)
      setSignedUrl('https://example.com/mock-manuscript.pdf')
      setIsLoading(false)
    }
    fetchUrl()
  }, [filePath])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin mb-4" />
        <p>Generating secure preview...</p>
      </div>
    )
  }

  return (
    <div className="w-full h-full overflow-hidden rounded-md border border-slate-200">
      {/* 嵌入原生 PDF 查看器 */}
      <iframe
        src={`${signedUrl}#toolbar=0`}
        className="w-full h-full"
        title="Manuscript PDF Preview"
      />
    </div>
  )
}
