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

  useEffect(() => {
    setFormData({
      orcid_id: user.orcid_id || "",
      google_scholar_url: user.google_scholar_url || "",
      research_interests: user.research_interests || [],
    })
  }, [user])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
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
          <p className="text-xs text-slate-500">
            These tags help us match you with relevant manuscripts.
          </p>
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t border-slate-100">
        <h3 className="font-medium text-slate-900">Academic Identity</h3>
        
        <div className="space-y-2">
          <Label htmlFor="orcid_id">ORCID iD</Label>
          <Input
            id="orcid_id"
            placeholder="0000-0000-0000-0000"
            value={formData.orcid_id}
            onChange={(e) => setFormData({ ...formData, orcid_id: e.target.value })}
            pattern="^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$"
          />
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
