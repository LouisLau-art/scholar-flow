"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { User } from "@/types/user"
import { Loader2 } from "lucide-react"

interface ProfileFormProps {
  user: User
  onSave: (data: Partial<User>) => void
  isSaving: boolean
}

export function ProfileForm({ user, onSave, isSaving }: ProfileFormProps) {
  const [formData, setFormData] = useState({
    full_name: user.full_name || "",
    title: user.title || "",
    affiliation: user.affiliation || "",
  })

  useEffect(() => {
    setFormData({
      full_name: user.full_name || "",
      title: user.title || "",
      affiliation: user.affiliation || "",
    })
  }, [user])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="full_name">Full Name</Label>
        <Input
          id="full_name"
          value={formData.full_name}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          required
          maxLength={100}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            placeholder="Dr., Prof., Mr., Ms."
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            maxLength={50}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="affiliation">Affiliation</Label>
          <Input
            id="affiliation"
            placeholder="University or Organization"
            value={formData.affiliation}
            onChange={(e) => setFormData({ ...formData, affiliation: e.target.value })}
            maxLength={200}
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
