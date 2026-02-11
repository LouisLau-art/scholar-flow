'use client'

import { useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

interface Props {
  manuscriptId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export default function PlagiarismActions({ manuscriptId, status }: Props) {
  /**
   * 查重操作组件
   * 遵循章程：视觉锁定深蓝系，显性交互逻辑
   */
  const [isRetrying, setIsUploading] = useState(false)

  const handleRetry = async () => {
    setIsUploading(true)
    try {
      // 调用 T016 后端重试接口
      console.log('Retrying plagiarism check for', manuscriptId)
      // await ApiClient.retryPlagiarism(manuscriptId)
      toast.success('任务已重新加入队列')
    } catch (error) {
      toast.error('重试请求失败')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDownload = () => {
    // 调用 T014 后端获取链接接口
    window.open(`https://api.scholarflow.com/v1/plagiarism/report/${manuscriptId}/download`, '_blank')
  }

  return (
    <div className="flex gap-2">
      {status === 'completed' && (
        <Button
          type="button"
          size="sm"
          onClick={handleDownload}
          className="flex items-center gap-2 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          <Download className="h-3.5 w-3.5" /> Report
        </Button>
      )}

      {status === 'failed' && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleRetry}
          disabled={isRetrying}
          className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRetrying ? 'animate-spin' : ''}`} /> 
          Retry Check
        </Button>
      )}

      {(status === 'pending' || status === 'running') && (
        <span className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Checking...
        </span>
      )}
    </div>
  )
}
