import { useState } from 'react'
import { Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

interface ReturnToAuthorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  targetId: string | null
  targetTitle: string | null
  onSubmit: (id: string, comment: string) => Promise<void>
}

export function ReturnToAuthorDialog({
  open,
  onOpenChange,
  targetId,
  targetTitle,
  onSubmit,
}: ReturnToAuthorDialogProps) {
  const [returning, setReturning] = useState(false)
  const [returnComment, setReturnComment] = useState('')
  const [returnConfirmText, setReturnConfirmText] = useState('')
  const [returnError, setReturnError] = useState('')

  const handleOpenChange = (isOpen: boolean) => {
    if (returning) return
    if (!isOpen) {
      setReturnComment('')
      setReturnConfirmText('')
      setReturnError('')
    }
    onOpenChange(isOpen)
  }

  const handleSubmit = async () => {
    if (!targetId) return
    const comment = returnComment.trim()
    if (!comment) {
      setReturnError('请填写退回原因，作者需要据此修订稿件。')
      return
    }
    if (returnConfirmText.trim() !== '退回') {
      setReturnError('请输入“退回”以确认该高风险操作。')
      return
    }
    
    setReturning(true)
    setReturnError('')
    
    try {
      await onSubmit(targetId, comment)
      handleOpenChange(false)
    } catch (err) {
      setReturnError(err instanceof Error ? err.message : '提交失败，请重试')
    } finally {
      setReturning(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>技术退回作者</DialogTitle>
          <DialogDescription>
            稿件将从入口审查直接退回作者修订，不进入 AE 外审阶段。请给出可执行的修改意见。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="rounded-lg border border-border bg-muted/40 p-3">
            <div className="text-xs text-muted-foreground">Manuscript</div>
            <div className="mt-1 text-sm font-medium text-foreground">{targetTitle || '-'}</div>
          </div>
          <div>
            <div className="mb-2 text-sm font-medium text-foreground">
              退回理由 <span className="text-red-600">*</span>
            </div>
            <Textarea
              value={returnComment}
              onChange={(e) => setReturnComment(e.target.value)}
              placeholder="例如：参考文献格式不符合期刊规范，伦理声明缺失，请按模板补齐后重投。"
              className="min-h-[140px]"
              disabled={returning}
            />
            {returnError ? <div className="mt-2 text-xs text-red-600">{returnError}</div> : null}
          </div>
          <div>
            <div className="mb-2 text-sm font-medium text-foreground">
              二次确认 <span className="text-red-600">*</span>
            </div>
            <Input
              value={returnConfirmText}
              onChange={(e) => setReturnConfirmText(e.target.value)}
              placeholder='请输入“退回”确认'
              disabled={returning}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={returning}>
            取消
          </Button>
          <Button variant="destructive" onClick={handleSubmit} disabled={returning}>
            {returning ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            确认退回
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
