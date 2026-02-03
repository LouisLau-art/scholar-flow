/**
 * 导出按钮组件
 * 功能: 下载分析报告（XLSX/CSV）
 *
 * 中文注释:
 * - 支持格式选择
 * - 下载进度提示
 * - 错误处理和 Toast 通知
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Download, FileSpreadsheet, FileText } from 'lucide-react'
import { toast } from 'sonner'
import { AnalyticsApi } from '@/lib/api/analytics'

interface ExportButtonProps {
  className?: string
}

export function ExportButton({ className }: ExportButtonProps) {
  const [exportingFormat, setExportingFormat] = useState<'xlsx' | 'csv' | null>(
    null,
  )

  const handleExport = async (format: 'xlsx' | 'csv') => {
    if (exportingFormat) return
    setExportingFormat(format)

    try {
      const blob = await AnalyticsApi.exportReport(format)

      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics_report.${format}`
      document.body.appendChild(a)
      a.click()

      // 清理
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success(`报告已下载`, {
        description: `analytics_report.${format}`,
      })
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('导出失败', {
        description: error instanceof Error ? error.message : '请稍后重试',
      })
    } finally {
      setExportingFormat(null)
    }
  }

  return (
    <div className={`flex gap-2 ${className || ''}`}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport('xlsx')}
        disabled={exportingFormat !== null}
      >
        <FileSpreadsheet className="h-4 w-4 mr-2" />
        {exportingFormat === 'xlsx' ? '导出中...' : 'Excel'}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport('csv')}
        disabled={exportingFormat !== null}
      >
        <FileText className="h-4 w-4 mr-2" />
        {exportingFormat === 'csv' ? '导出中...' : 'CSV'}
      </Button>
    </div>
  )
}
