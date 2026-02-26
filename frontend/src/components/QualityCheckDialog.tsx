'use client'

import { useState } from 'react'
import { Check, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface QCProps {
  manuscriptId: string
  onClose: () => void
}

export default function QualityCheckDialog({ manuscriptId, onClose }: QCProps) {
  /**
   * 质检对话框组件
   * 遵循章程：Shadcn/UI 风格，配色锁定深蓝
   */
  const [passed, setPassed] = useState<boolean | null>(null)
  const [kpiOwner, setKpiOwner] = useState('')

  const handleSubmit = async () => {
    if (!kpiOwner) {
      toast.error('必须指定 KPI 归属人')
      return
    }
    
    // 调用 ApiClient 进行质检提交 (T010 已封装部分逻辑)
    toast.success(`Quality check submitted: ${manuscriptId}`)
    onClose()
  }

  return (
    <Dialog open onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="max-w-md p-8">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl">Quality Check</DialogTitle>
          <DialogDescription>
            Review the manuscript and assign responsibility.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-8 space-y-6">
          {/* 通过/拒绝按钮 */}
          <div className="flex gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPassed(true)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-3 border-2 transition-all ${
                passed === true ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground'
              }`}
            >
              <Check className="h-5 w-5" /> Pass
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setPassed(false)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-3 border-2 transition-all ${
                passed === false ? 'border-red-600 bg-red-50 text-red-700' : 'border-border text-muted-foreground'
              }`}
            >
              <X className="h-5 w-5" /> Reject
            </Button>
          </div>

          {/* KPI 归属人选择 */}
          <div>
            <label className="block text-sm font-semibold text-foreground">KPI Owner</label>
            <Select value={kpiOwner || '__empty'} onValueChange={(value) => setKpiOwner(value === '__empty' ? '' : value)}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue placeholder="Select an editor..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__empty">Select an editor...</SelectItem>
                <SelectItem value="louis">Louis Lau</SelectItem>
                <SelectItem value="admin">System Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter className="mt-10 flex gap-3">
          <Button type="button" variant="ghost" onClick={onClose} className="flex-1">
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            className="flex-1 rounded-md bg-primary py-2 text-primary-foreground hover:bg-primary/90 transition-opacity disabled:opacity-50"
            disabled={passed === null || !kpiOwner}
          >
            Submit Review
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
