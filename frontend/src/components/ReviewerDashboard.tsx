"use client"

import { useState, useEffect } from "react"
import { Star, FileText, Send } from "lucide-react"
import { toast } from "sonner"
import { authService } from "@/services/auth"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { FileUpload } from "@/components/FileUpload"

interface ReviewTask {
  id: string
  manuscript_id: string
  manuscripts?: {
    title: string
    abstract: string
    file_path?: string | null
  } | null
}

type ReviewData = {
  novelty: number
  rigor: number
  language: number
  commentsForAuthor: string
  confidentialCommentsToEditor: string
  attachment: File | null
}

function ReviewModal({
  task,
  onClose,
  onSubmitted,
}: {
  task: ReviewTask
  onClose: () => void
  onSubmitted: () => void
}) {
  const [reviewData, setReviewData] = useState<ReviewData>({
    novelty: 3,
    rigor: 3,
    language: 3,
    commentsForAuthor: '',
    confidentialCommentsToEditor: '',
    attachment: null,
  })

  const handleSubmit = async () => {
    if (!reviewData.commentsForAuthor.trim()) {
      toast.error("Comments for the Authors is required.")
      return
    }

    const toastId = toast.loading("Submitting review...")
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.", { id: toastId })
        return
      }

      let attachmentPath: string | null = null
      if (reviewData.attachment) {
        const fd = new FormData()
        fd.set("attachment", reviewData.attachment)
        const uploadRes = await fetch(`/api/v1/reviews/assignments/${encodeURIComponent(task.id)}/attachment`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        })
        const uploadJson = await uploadRes.json().catch(() => null)
        if (!uploadRes.ok || !uploadJson?.success || !uploadJson?.data?.attachment_path) {
          toast.error(uploadJson?.detail || uploadJson?.message || "Attachment upload failed.", { id: toastId })
          return
        }
        attachmentPath = uploadJson.data.attachment_path
      }

      const res = await fetch("/api/v1/reviews/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          assignment_id: task.id,
          scores: { novelty: reviewData.novelty, rigor: reviewData.rigor, language: reviewData.language },
          comments_for_author: reviewData.commentsForAuthor,
          confidential_comments_to_editor: reviewData.confidentialCommentsToEditor || null,
          attachment_path: attachmentPath,
        }),
      })
      const result = await res.json().catch(() => null)
      if (!res.ok || !result?.success) {
        toast.error(result?.detail || result?.message || "Submit failed. Please try again.", { id: toastId })
        return
      }
      toast.success("Review submitted. Thank you!", { id: toastId })
      onClose()
      onSubmitted()
    } catch (e) {
      toast.error("Submit failed. Please try again.", { id: toastId })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-[720px] rounded-3xl bg-white p-6 sm:p-8 shadow-2xl min-h-[600px] max-h-[92vh] overflow-y-auto">
        <div className="mb-6">
          <h4 className="font-serif text-2xl">Structured Peer Review</h4>
          <p className="text-sm text-slate-500">
            Submit your professional assessment for &quot;{task.manuscripts?.title}&quot;
          </p>
        </div>

        <div className="py-2 space-y-6 sm:space-y-8">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-slate-700">Novelty & Originality</Label>
              <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.novelty}/5</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={reviewData.novelty}
              onChange={(e) => setReviewData({ ...reviewData, novelty: parseInt(e.target.value) })}
              className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-slate-700">Technical Rigor</Label>
              <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.rigor}/5</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={reviewData.rigor}
              onChange={(e) => setReviewData({ ...reviewData, rigor: parseInt(e.target.value) })}
              className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-slate-700">Language Quality</Label>
              <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.language}/5</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={reviewData.language}
              onChange={(e) => setReviewData({ ...reviewData, language: parseInt(e.target.value) })}
              className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          <div className="space-y-3">
            <Label className="font-semibold text-slate-700">Comments for the Authors</Label>
            <textarea
              placeholder="Provide detailed feedback for the authors..."
              className="min-h-[140px] sm:min-h-[160px] w-full rounded-2xl border border-slate-200 p-3 focus:ring-2 focus:ring-blue-500"
              value={reviewData.commentsForAuthor}
              onChange={(e) => setReviewData({ ...reviewData, commentsForAuthor: e.target.value })}
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label className="font-semibold text-slate-700">Confidential Comments to the Editor</Label>
              <span className="text-xs font-semibold text-red-600">Authors will NOT see this</span>
            </div>
            <textarea
              placeholder="Optional notes for editor only..."
              className="min-h-[110px] w-full rounded-2xl border border-slate-200 p-3 focus:ring-2 focus:ring-blue-500"
              value={reviewData.confidentialCommentsToEditor}
              onChange={(e) => setReviewData({ ...reviewData, confidentialCommentsToEditor: e.target.value })}
            />
          </div>

          <FileUpload
            label="Upload Annotated PDF (Optional)"
            helperText="Only Editors and you (the Reviewer) can download this file."
            accept="application/pdf"
            file={reviewData.attachment}
            onFileSelected={(file) => setReviewData({ ...reviewData, attachment: file })}
          />
        </div>

        <div className="mt-8 flex flex-col-reverse sm:flex-row justify-end gap-3">
          <Button onClick={onClose} variant="ghost" className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="w-full sm:w-auto">
            Submit Decision <Send className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function ReviewerDashboard() {
  const [tasks, setTasks] = useState<ReviewTask[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<ReviewTask | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewTitle, setPreviewTitle] = useState("")
  const [previewLoading, setPreviewLoading] = useState(false)

  const fetchTasks = async () => {
    try {
      const session = await authService.getSession()
      const userId = session?.user?.id
      if (!userId) {
        setTasks([])
        toast.error("Please sign in to view reviewer tasks.")
        return
      }
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/my-tasks?user_id=${encodeURIComponent(userId)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const data = await res.json()
      setTasks(data.data || [])
    } catch (e) {
      toast.error("Failed to load tasks.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleOpenPreview = async (task: ReviewTask) => {
    if (!task?.manuscripts?.file_path) {
      toast.error("该稿件没有可预览的 PDF（file_path 为空）。请让 Editor 重新上传/绑定文件。")
      return
    }
    setIsPreviewOpen(true)
    setPreviewTitle(task?.manuscripts?.title || "Full Text Preview")
    setPreviewUrl(null)
    setPreviewLoading(true)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.")
        return
      }
      const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(task.manuscript_id)}/pdf-signed`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success || !json?.data?.signed_url) {
        toast.error(json?.detail || json?.message || "Preview not available. Please download the PDF.")
        return
      }
      setPreviewUrl(json.data.signed_url)
    } catch (e) {
      toast.error("Preview failed. Please try again.")
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleClosePreview = () => {
    setIsPreviewOpen(false)
    setPreviewUrl(null)
    setPreviewTitle("")
  }

  return (
    <div className="space-y-6">
      {/* ... 之前的 Header 代码 ... */}
      
      {tasks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center text-slate-500">
          No review tasks assigned to your account yet. Ask the editor to assign you as a reviewer.
        </div>
      ) : (
        <div className="grid gap-4">
          {tasks.map((task) => (
            <div key={task.id} className="rounded-2xl border border-slate-200 bg-white hover:shadow-md transition-shadow">
            <div className="flex flex-row items-start justify-between space-y-0 p-6">
              <div className="space-y-1">
                <h3 className="text-xl font-serif font-semibold">{task.manuscripts?.title}</h3>
                <p className="line-clamp-2 italic text-sm text-slate-500">{task.manuscripts?.abstract}</p>
              </div>
              <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">PENDING REVIEW</span>
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-50 p-6">
              <Button
                onClick={() => handleOpenPreview(task)}
                variant="outline"
                size="sm"
                className="gap-2"
                disabled={!task.manuscripts?.file_path}
              >
                <FileText className="h-4 w-4" /> Read Full Text
              </Button>
              
              <Button
                onClick={() => {
                  setSelectedTask(task)
                  setIsModalOpen(true)
                }}
                size="sm"
                className="gap-2"
              >
                <Star className="h-4 w-4" /> Start Review
              </Button>
            </div>
            </div>
          ))}
        </div>
      )}

      {isPreviewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={handleClosePreview} />
          <div className="relative w-full max-w-5xl rounded-3xl bg-white p-6 sm:p-8 shadow-2xl h-[80vh] max-h-[90vh] flex flex-col">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h4 className="font-serif text-2xl text-slate-900">Full Text Preview</h4>
                <p className="text-sm text-slate-500">{previewTitle || "Manuscript preview"}</p>
              </div>
              <Button
                onClick={handleClosePreview}
                variant="outline"
                size="sm"
              >
                Close
              </Button>
            </div>

            <div className="mt-6 flex-1 min-h-0 rounded-2xl bg-slate-100 border border-slate-200 overflow-hidden">
              {previewLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500 font-medium">
                  Loading preview...
                </div>
              ) : previewUrl ? (
                <iframe src={previewUrl} className="w-full h-full border-0" title="PDF Preview" />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500 font-medium">No PDF available for preview.</p>
                  </div>
                </div>
              )}
            </div>
            <p className="mt-4 text-xs text-slate-400">Preview links expire in 5 minutes.</p>
          </div>
        </div>
      )}

      {isModalOpen && selectedTask && (
        <ReviewModal
          key={selectedTask.manuscript_id}
          task={selectedTask}
          onClose={() => {
            setIsModalOpen(false)
            setSelectedTask(null)
          }}
          onSubmitted={() => fetchTasks()}
        />
      )}
    </div>
  )
}
