"use client"

import { useState, useRef } from "react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { storageService } from "@/services/storage"
import { Upload, Loader2, Image as ImageIcon } from "lucide-react"
import { toast } from "sonner"
import { compressImage } from "@/lib/image-utils"

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

    // Basic type validation
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file.')
      return
    }

    try {
      setIsUploading(true)
      
      // Compress/Resize image (Standardize to max 800x800 JPEG)
      // This handles files > 2MB automatically
      const processedFile = await compressImage(file, 800, 800, 0.8)

      const url = await storageService.uploadAvatar(userId, processedFile)
      onUploadSuccess(url)
      toast.success('Avatar updated successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to process or upload avatar')
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
            accept="image/png, image/jpeg, image/webp"
            onChange={handleFileSelect}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Supported formats: JPG, PNG, WEBP.
        </p>
      </div>
    </div>
  )
}
