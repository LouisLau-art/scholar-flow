"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { FileUpload } from "@/components/FileUpload"
import { authService } from "@/services/auth"

type Props = {
  manuscriptId: string
  manuscriptTitle?: string | null
  disabled?: boolean
  onUploaded?: (finalPdfPath: string) => void
}

export default function ProductionUploadDialog({ manuscriptId, manuscriptTitle, disabled, onUploaded }: Props) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleUpload = async () => {
    if (!file) {
      toast.error("请选择一个 PDF 文件。")
      return
    }
    setIsUploading(true)
    const toastId = toast.loading("Uploading production PDF…")
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.", { id: toastId })
        return
      }
      const fd = new FormData()
      fd.append("file", file)
      const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/production-file`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: fd,
      })
      const raw = await res.text().catch(() => "")
      let json: any = null
      try {
        json = raw ? JSON.parse(raw) : null
      } catch {
        json = null
      }

      if (!res.ok || json?.success === false) {
        const msg = json?.detail || json?.message || (raw && raw.trim() ? raw.trim() : `HTTP ${res.status}`)
        toast.error(msg, { id: toastId })
        return
      }

      const path = String(json?.data?.final_pdf_path || "")
      toast.success("Production PDF uploaded.", { id: toastId })
      setOpen(false)
      setFile(null)
      if (path) onUploaded?.(path)
    } catch (e) {
      toast.error("Upload failed.", { id: toastId })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" disabled={disabled} type="button">
          Upload Final PDF
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Production Upload</DialogTitle>
          <DialogDescription>
            Upload the final typeset PDF for: <span className="font-semibold">{manuscriptTitle || manuscriptId}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          <FileUpload
            label="Final PDF"
            helperText="Only PDF is supported. Uploading again will replace the active final PDF reference."
            accept="application/pdf"
            disabled={isUploading}
            isBusy={isUploading}
            file={file}
            onFileSelected={setFile}
          />
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => setOpen(false)} disabled={isUploading}>
            Cancel
          </Button>
          <Button type="button" onClick={handleUpload} disabled={isUploading || !file}>
            {isUploading ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

