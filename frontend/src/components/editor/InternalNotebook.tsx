'use client'

import { useEffect, useMemo, useState } from 'react'
import { format } from 'date-fns'
import { Check, Loader2, MessageSquare, Search, Send, UserRoundPlus, X } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { EditorApi } from '@/services/editorApi'
import type { InternalComment } from '@/types/internal-collaboration'

type StaffOption = {
  id: string
  full_name?: string
  email?: string
}

interface InternalNotebookProps {
  manuscriptId: string
  onCommentPosted?: () => void
}

function initials(value: string): string {
  const clean = value.trim()
  if (!clean) return '?'
  return clean.slice(0, 2).toUpperCase()
}

export function InternalNotebook({ manuscriptId, onCommentPosted }: InternalNotebookProps) {
  const [comments, setComments] = useState<InternalComment[]>([])
  const [loading, setLoading] = useState(false)
  const [inputText, setInputText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [staff, setStaff] = useState<StaffOption[]>([])
  const [mentionUserIds, setMentionUserIds] = useState<string[]>([])
  const [staffSearch, setStaffSearch] = useState('')

  const staffById = useMemo(() => {
    const map = new Map<string, StaffOption>()
    for (const member of staff) map.set(member.id, member)
    return map
  }, [staff])

  const selectedMentionLabels = useMemo(
    () =>
      mentionUserIds.map((id) => {
        const member = staffById.get(id)
        return member?.full_name || member?.email || id
      }),
    [mentionUserIds, staffById]
  )
  const filteredStaff = useMemo(() => {
    const key = staffSearch.trim().toLowerCase()
    if (!key) return staff
    return staff.filter((member) => {
      const name = String(member.full_name || '').toLowerCase()
      const email = String(member.email || '').toLowerCase()
      return name.includes(key) || email.includes(key)
    })
  }, [staff, staffSearch])

  async function loadComments() {
    try {
      setLoading(true)
      const res = await EditorApi.getInternalComments(manuscriptId)
      if (res?.success) {
        const next = Array.isArray(res.data) ? (res.data as InternalComment[]) : []
        setComments(next)
      }
    } catch (error) {
      console.error('Failed to load comments', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadStaffOptions() {
    try {
      const res = await EditorApi.listInternalStaff('')
      if (!res?.success) return
      setStaff(Array.isArray(res.data) ? res.data : [])
    } catch {
      // ignore and keep notebook usable without mention dropdown
    }
  }

  useEffect(() => {
    loadComments()
    loadStaffOptions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  function validateMentions(): string | null {
    const unique = new Set(mentionUserIds)
    if (unique.size !== mentionUserIds.length) {
      return 'Duplicate mentions are not allowed.'
    }
    const invalid = mentionUserIds.filter((id) => !staffById.has(id))
    if (invalid.length > 0) {
      return 'Contains invalid mention targets.'
    }
    return null
  }

  function toggleMention(userId: string) {
    setMentionUserIds((prev) => (prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]))
  }

  async function handlePost() {
    const content = inputText.trim()
    if (!content) return

    const mentionError = validateMentions()
    if (mentionError) {
      toast.error(mentionError)
      return
    }

    try {
      setSubmitting(true)
      const res = await EditorApi.postInternalCommentWithMentions(manuscriptId, {
        content,
        mention_user_ids: mentionUserIds,
      })
      if (res?.success && res?.data) {
        setComments((prev) => [...prev, res.data as InternalComment])
        setInputText('')
        setMentionUserIds([])
        onCommentPosted?.()
      } else {
        const detail = res?.detail
        if (detail && typeof detail === 'object' && Array.isArray((detail as { invalid_user_ids?: string[] }).invalid_user_ids)) {
          toast.error('Contains invalid mention targets.')
        } else {
          toast.error(res?.detail || res?.message || 'Failed to post comment')
        }
      }
    } catch {
      toast.error('Error posting comment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="flex h-full flex-col shadow-sm">
      <CardHeader className="border-b py-4">
        <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-700">
          <MessageSquare className="h-4 w-4" />
          Internal Notebook (Staff Only)
        </CardTitle>
      </CardHeader>
      <CardContent className="flex h-[440px] flex-1 flex-col gap-3 p-4">
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          Tip: select teammates below to create validated mentions. Duplicate and invalid mentions are blocked.
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto pr-2">
          {loading && comments.length === 0 ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            </div>
          ) : comments.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-400">No internal notes yet.</div>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="group flex gap-3">
                <div className="h-8 w-8 flex-shrink-0 rounded-full bg-blue-100 text-xs font-bold uppercase text-blue-600 flex items-center justify-center">
                  {initials(comment.user?.full_name || comment.user?.email || '?')}
                </div>
                <div className="w-full rounded-lg rounded-tl-none border border-slate-100 bg-slate-50 p-3 transition-colors hover:bg-slate-100">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">
                      {comment.user?.full_name || comment.user?.email || 'Unknown'}
                    </span>
                    <span className="text-[10px] text-slate-400">{format(new Date(comment.created_at), 'MMM d, HH:mm')}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">{comment.content}</p>
                  {(comment.mention_user_ids || []).length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1" data-testid="notebook-mentions">
                      {(comment.mention_user_ids || []).map((uid) => {
                        const member = staffById.get(uid)
                        const text = member?.full_name || member?.email || uid
                        return (
                          <span
                            key={`${comment.id}-${uid}`}
                            className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700"
                          >
                            @{text}
                          </span>
                        )
                      })}
                    </div>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="mt-auto space-y-2 border-t pt-2">
          <div>
            <Label className="mb-1 inline-flex items-center gap-1 text-xs text-slate-600">
              <UserRoundPlus className="h-3.5 w-3.5" /> Mention teammates
            </Label>
            <div className="rounded-md border border-slate-200 bg-white p-2">
              <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5">
                <Search className="h-3.5 w-3.5 text-slate-500" />
                <Input
                  aria-label="Search teammates"
                  placeholder="Search by name or email..."
                  value={staffSearch}
                  onChange={(e) => setStaffSearch(e.target.value)}
                  className="h-6 border-0 bg-transparent px-0 text-xs shadow-none focus-visible:ring-0"
                />
              </div>

              {mentionUserIds.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {mentionUserIds.map((uid) => {
                    const member = staffById.get(uid)
                    const text = member?.full_name || member?.email || uid
                    return (
                      <span
                        key={`selected-${uid}`}
                        className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700"
                      >
                        @{text}
                        <button
                          type="button"
                          aria-label={`Remove ${text}`}
                          onClick={() => toggleMention(uid)}
                          className="rounded-full p-0.5 text-blue-600 transition hover:bg-blue-100"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    )
                  })}
                </div>
              ) : (
                <p className="mt-2 text-[11px] text-slate-500">No teammates selected.</p>
              )}

              <div className="mt-2 max-h-28 overflow-y-auto rounded-md border border-slate-200">
                {filteredStaff.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-slate-500">No teammates found.</div>
                ) : (
                  filteredStaff.map((member) => {
                    const text = member.full_name || member.email || member.id
                    const selected = mentionUserIds.includes(member.id)
                    return (
                      <button
                        key={member.id}
                        type="button"
                        aria-label={`Mention ${text}`}
                        className={`flex w-full items-center justify-between border-b border-slate-100 px-3 py-2 text-left text-xs transition last:border-b-0 ${
                          selected ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-50'
                        }`}
                        onClick={() => toggleMention(member.id)}
                      >
                        <span className="truncate">{text}</span>
                        {selected ? <Check className="h-3.5 w-3.5 flex-shrink-0" /> : null}
                      </button>
                    )
                  })
                )}
              </div>
            </div>
            {selectedMentionLabels.length > 0 ? (
              <p className="mt-1 text-[11px] text-slate-500">Selected {selectedMentionLabels.length} teammate(s).</p>
            ) : null}
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Type an internal note..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handlePost()
                }
              }}
              disabled={submitting}
              className="flex-1"
            />
            <Button aria-label="Post internal note" onClick={handlePost} disabled={submitting || !inputText.trim()} size="icon">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
