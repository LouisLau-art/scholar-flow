'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { MessageSquare, Loader2, Send } from 'lucide-react'
import { format } from 'date-fns'

interface InternalComment {
  id: string
  content: string
  created_at: string
  user?: {
    full_name?: string
    email?: string
  }
}

interface InternalNotebookProps {
  manuscriptId: string
}

export function InternalNotebook({ manuscriptId }: InternalNotebookProps) {
  const [comments, setComments] = useState<InternalComment[]>([])
  const [loading, setLoading] = useState(false)
  const [inputText, setInputText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function loadComments() {
    try {
      setLoading(true)
      const res = await EditorApi.getInternalComments(manuscriptId)
      if (res?.success) {
        const next = Array.isArray(res.data) ? res.data : []
        setComments(next)
      }
    } catch (e) {
      console.error('Failed to load comments', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadComments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  async function handlePost() {
    if (!inputText.trim()) return
    try {
      setSubmitting(true)
      const res = await EditorApi.postInternalComment(manuscriptId, inputText)
      if (res?.success && res?.data) {
        setComments((prev) => [...prev, res.data])
        setInputText('')
        // Scroll to bottom?
      } else {
        toast.error('Failed to post comment')
      }
    } catch (e) {
      toast.error('Error posting comment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="h-full flex flex-col shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
          <MessageSquare className="h-4 w-4" />
          Internal Notebook (Staff Only)
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-4 gap-4 h-[400px]">
        {/* Comments List */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {loading && comments.length === 0 ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            </div>
          ) : comments.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-8">No internal notes yet.</div>
          ) : (
            comments.map((c) => (
              <div key={c.id} className="flex gap-3 group">
                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold flex-shrink-0 uppercase">
                  {(c.user?.full_name || c.user?.email || '?').substring(0, 2)}
                </div>
                <div className="bg-slate-50 p-3 rounded-lg rounded-tl-none border border-slate-100 w-full hover:bg-slate-100 transition-colors">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-bold text-slate-700">
                      {c.user?.full_name || c.user?.email || 'Unknown'}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {format(new Date(c.created_at), 'MMM d, HH:mm')}
                    </span>
                  </div>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{c.content}</p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Area */}
        <div className="flex gap-2 pt-2 border-t mt-auto">
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
          <Button onClick={handlePost} disabled={submitting || !inputText.trim()} size="icon">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
