"use client"

import { useState, useRef } from "react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { storageService } from "@/services/storage"
import { Upload, Loader2, Image as ImageIcon } from "lucide-react"
import { toast } from "sonner"

interface AvatarUploadProps {
  userId: string
  currentAvatarUrl?: string | null
  onUploadSuccess: (url: string) => void
  userName?: string
}

export function AvatarUpload({ userId, currentAvatarUrl, onUploadSuccess, userName }: AvatarUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validation
    const validTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type)) {
      toast.error('Invalid file type. Please use JPG, PNG, or WEBP.')
      return
    }

    if (file.size > 2 * 1024 * 1024) {
      toast.error('File too large. Max size is 2MB.')
      return
    }

    try {
      setIsUploading(true)
      const url = await storageService.uploadAvatar(userId, file)
      onUploadSuccess(url)
      toast.success('Avatar updated successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to upload avatar')
    } finally {
      setIsUploading(false)
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="flex items-center gap-6">
      <Avatar className="h-24 w-24 border-2 border-slate-100">
        <AvatarImage src={currentAvatarUrl || undefined} />
        <AvatarFallback className="text-xl bg-slate-100 text-slate-400">
          {userName?.charAt(0).toUpperCase() || <ImageIcon className="h-8 w-8" />}
        </AvatarFallback>
      </Avatar>

      <div className="space-y-2">
        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            Change Avatar
          </Button>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".jpg,.jpeg,.png,.webp"
            onChange={handleFileSelect}
          />
        </div>
        <p className="text-xs text-slate-500">
          JPG, PNG or WEBP. Max 2MB.
        </p>
      </div>
    </div>
  )
}
