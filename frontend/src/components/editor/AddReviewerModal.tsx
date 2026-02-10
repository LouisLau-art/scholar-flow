'use client'

import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TagInput } from '@/components/ui/TagInput'
import { Select } from '@/components/ui/select'

type Mode = 'create' | 'edit'

export type ReviewerLibraryFormValues = {
  id?: string
  email: string
  full_name: string
  title: string
  affiliation?: string
  homepage_url?: string
  research_interests?: string[]
}

const TITLE_OPTIONS = ['Prof.', 'Professor', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Mx.', 'Other'] as const

function isValidHttpUrl(value: string) {
  try {
    const u = new URL(value)
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}

export function AddReviewerModal(props: {
  open: boolean
  onOpenChange: (next: boolean) => void
  mode?: Mode
  initial?: Partial<ReviewerLibraryFormValues>
  onSaved?: () => void
}) {
  const mode: Mode = props.mode || (props.initial?.id ? 'edit' : 'create')
  const [isSaving, setIsSaving] = useState(false)

  const [email, setEmail] = useState(props.initial?.email || '')
  const [fullName, setFullName] = useState(props.initial?.full_name || '')
  const [title, setTitle] = useState(props.initial?.title || 'Dr.')
  const [affiliation, setAffiliation] = useState(props.initial?.affiliation || '')
  const [homepageUrl, setHomepageUrl] = useState(props.initial?.homepage_url || '')
  const [interests, setInterests] = useState<string[]>(props.initial?.research_interests || [])

  const canSubmit = useMemo(() => {
    if (!email.trim()) return false
    if (!fullName.trim()) return false
    if (!title.trim()) return false
    if (homepageUrl.trim() && !isValidHttpUrl(homepageUrl.trim())) return false
    return true
  }, [email, fullName, homepageUrl, title])

  const handleSubmit = async () => {
    if (!canSubmit) return
    setIsSaving(true)
    const toastId = toast.loading(mode === 'create' ? 'Adding reviewer...' : 'Saving reviewer...')
    try {
      if (mode === 'create') {
        const res = await EditorApi.addReviewerToLibrary({
          email: email.trim(),
          full_name: fullName.trim(),
          title: title.trim(),
          affiliation: affiliation.trim() || undefined,
          homepage_url: homepageUrl.trim() || undefined,
          research_interests: interests,
        })
        if (!res?.success) throw new Error(res?.detail || res?.message || 'Add failed')
      } else {
        const id = props.initial?.id
        if (!id) throw new Error('Missing reviewer id')
        const res = await EditorApi.updateReviewerLibraryItem(id, {
          full_name: fullName.trim(),
          title: title.trim(),
          affiliation: affiliation.trim() || null,
          homepage_url: homepageUrl.trim() || null,
          research_interests: interests,
        })
        if (!res?.success) throw new Error(res?.detail || res?.message || 'Update failed')
      }

      toast.success(mode === 'create' ? 'Reviewer added to library' : 'Reviewer updated', { id: toastId })
      props.onOpenChange(false)
      props.onSaved?.()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed', { id: toastId })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'Add Reviewer to Library' : 'Edit Reviewer'}</DialogTitle>
          <DialogDescription>
            {mode === 'create'
              ? 'Only records the reviewer profile. No invitation email will be sent.'
              : 'Update reviewer metadata used for matching and assignment.'}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Title</label>
              <Select
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              >
                {TITLE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Full Name</label>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Louis Lau" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Email</label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@university.edu"
                disabled={mode === 'edit'}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Affiliation</label>
              <Input value={affiliation} onChange={(e) => setAffiliation(e.target.value)} placeholder="University / Institute" />
            </div>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">Homepage URL</label>
            <Input value={homepageUrl} onChange={(e) => setHomepageUrl(e.target.value)} placeholder="https://..." />
            {homepageUrl.trim() && !isValidHttpUrl(homepageUrl.trim()) && (
              <div className="text-xs text-red-600">Please enter a valid http(s) URL.</div>
            )}
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">Research Interests</label>
            <TagInput tags={interests} setTags={setInterests} placeholder="Type keyword and press Enter" maxTags={20} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => props.onOpenChange(false)} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isSaving}>
            {isSaving ? 'Saving...' : mode === 'create' ? 'Add to Library' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
