"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { TagInput } from "@/components/ui/TagInput"
import { User } from "@/types/user"
import { Loader2 } from "lucide-react"

interface AcademicFormProps {
  user: User
  onSave: (data: Partial<User>) => void
  isSaving: boolean
}

export function AcademicForm({ user, onSave, isSaving }: AcademicFormProps) {
  const [formData, setFormData] = useState({
    orcid_id: user.orcid_id || "",
    google_scholar_url: user.google_scholar_url || "",
    research_interests: user.research_interests || [],
  })
  const [errors, setErrors] = useState<{ orcid_id?: string; google_scholar_url?: string }>({})

  useEffect(() => {
    setFormData({
      orcid_id: user.orcid_id || "",
      google_scholar_url: user.google_scholar_url || "",
      research_interests: user.research_interests || [],
    })
    setErrors({})
  }, [user])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})

    const orcid = formData.orcid_id.trim()
    const scholarUrl = formData.google_scholar_url.trim()

    if (orcid && !/^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/.test(orcid)) {
      setErrors({ orcid_id: "格式不正确（示例：0000-0000-0000-0000），也可以留空" })
      return
    }
    if (scholarUrl) {
      try {
        // 仅做基本 URL 校验，域名不强制限制
        new URL(scholarUrl)
      } catch {
        setErrors({ google_scholar_url: "不是有效链接，也可以留空" })
        return
      }
    }

    onSave({
      ...formData,
      // Use undefined to omit fields from JSON, allowing Pydantic default (None) to apply
      google_scholar_url: scholarUrl || undefined,
      orcid_id: orcid || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>Research Interests</Label>
          <TagInput
            placeholder="Add a topic (e.g., Artificial Intelligence)"
            tags={formData.research_interests}
            setTags={(tags) => setFormData({ ...formData, research_interests: tags })}
            maxTags={10}
            maxLength={50}
          />
          <p className="text-xs text-muted-foreground">
            These tags help us match you with relevant manuscripts.
          </p>
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t border-border">
        <h3 className="font-medium text-foreground">Academic Identity</h3>
        
        <div className="space-y-2">
          <Label htmlFor="orcid_id">ORCID iD</Label>
          <Input
            id="orcid_id"
            placeholder="0000-0000-0000-0000"
            value={formData.orcid_id}
            onChange={(e) => setFormData({ ...formData, orcid_id: e.target.value })}
            pattern="^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$"
          />
          {errors.orcid_id && <p className="text-xs text-destructive">{errors.orcid_id}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="google_scholar_url">Google Scholar URL</Label>
          <Input
            id="google_scholar_url"
            type="url"
            placeholder="https://scholar.google.com/citations?user=..."
            value={formData.google_scholar_url}
            onChange={(e) => setFormData({ ...formData, google_scholar_url: e.target.value })}
          />
          {errors.google_scholar_url && (
            <p className="text-xs text-destructive">{errors.google_scholar_url}</p>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={isSaving}>
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save Changes
        </Button>
      </div>
    </form>
  )
}
