'use client'

import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { Loader2, Upload } from 'lucide-react'
import { EditorApi } from '@/services/editorApi'

export function UploadReviewFile({
  manuscriptId,
  onUploaded,
}: {
  manuscriptId: string
  onUploaded?: () => void
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [uploading, setUploading] = useState(false)

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={async (e) => {
          const file = e.target.files?.[0]
          if (!file) return
          try {
            setUploading(true)
            const res = await EditorApi.uploadPeerReviewFile(manuscriptId, file)
            if (!res?.success) throw new Error(res?.detail || res?.message || 'Upload failed')
            toast.success('Peer review file uploaded')
            onUploaded?.()
          } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Upload failed')
          } finally {
            setUploading(false)
            if (inputRef.current) inputRef.current.value = ''
          }
        }}
      />

      <Button
        size="sm"
        variant="outline"
        className="gap-2"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        data-testid="upload-review-file"
      >
        {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
        {uploading ? 'Uploading…' : 'Upload'}
      </Button>
    </>
  )
}

