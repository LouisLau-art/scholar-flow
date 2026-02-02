"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

interface PasswordChangeFormProps {
  onSave: (password: string) => Promise<void>
}

export function PasswordChangeForm({ onSave }: PasswordChangeFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [formData, setFormData] = useState({
    password: "",
    confirm_password: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (formData.password.length < 8) {
      toast.error("Password must be at least 8 characters long")
      return
    }

    if (formData.password !== formData.confirm_password) {
      toast.error("Passwords do not match")
      return
    }

    try {
      setIsSaving(true)
      await onSave(formData.password)
      setFormData({ password: "", confirm_password: "" })
      toast.success("Password updated successfully")
    } catch (error) {
      // Error handled by parent or service usually, but here we catch to stop loading
      console.error(error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="password">New Password</Label>
        <Input
          id="password"
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          required
          minLength={8}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirm New Password</Label>
        <Input
          id="confirm_password"
          type="password"
          value={formData.confirm_password}
          onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
          required
          minLength={8}
        />
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={isSaving || !formData.password}>
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Update Password
        </Button>
      </div>
    </form>
  )
}
