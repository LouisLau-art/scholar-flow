"use client"

import { useRef } from "react"
import { Upload, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

type Props = {
  label: string
  helperText?: string
  accept?: string
  disabled?: boolean
  isBusy?: boolean
  file: File | null
  onFileSelected: (file: File | null) => void
}

export function FileUpload({
  label,
  helperText,
  accept,
  disabled,
  isBusy,
  file,
  onFileSelected,
}: Props) {
  const ref = useRef<HTMLInputElement>(null)

  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold text-slate-900">{label}</div>
      {helperText ? <div className="text-xs text-slate-500">{helperText}</div> : null}

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-2"
          disabled={disabled || isBusy}
          onClick={() => ref.current?.click()}
        >
          {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          Choose file
        </Button>

        <div className="text-sm text-slate-600 flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-400" />
          <span className="break-all">{file?.name || "No file selected"}</span>
        </div>
      </div>

      <input
        ref={ref}
        type="file"
        className="hidden"
        accept={accept}
        onChange={(e) => onFileSelected(e.target.files?.[0] ?? null)}
      />
    </div>
  )
}

