"use client"

import { useState, useEffect } from "react"
import { Star, FileText, Send } from "lucide-react"
import { toast } from "sonner"
import { authService } from "@/services/auth"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

interface ReviewTask {
  id: string
  manuscript_id: string
  manuscripts: {
    title: string
    abstract: string
  }
}

export default function ReviewerDashboard() {
  const [tasks, setTasks] = useState<ReviewTask[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<any>(null)
  const [reviewData, setReviewReviewData] = useState({ novelty: 3, rigor: 3, language: 3, comments: "" })
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

  const handleOpenPreview = async (task: any) => {
    setIsPreviewOpen(true)
    setPreviewTitle(task?.manuscripts?.title || "Full Text Preview")
    setPreviewUrl(null)
    setPreviewLoading(true)
    const filePath = task?.manuscripts?.file_path
    if (!filePath) {
      setPreviewLoading(false)
      return
    }
    try {
      const { data, error } = await supabase.storage
        .from("manuscripts")
        .createSignedUrl(filePath, 60 * 5)
      if (error || !data?.signedUrl) {
        toast.error("Preview not available. Please download the PDF.")
        setPreviewLoading(false)
        return
      }
      setPreviewUrl(data.signedUrl)
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

  const handleSubmitReview = async () => {
    const toastId = toast.loading("Submitting review...")
    try {
      const token = await authService.getAccessToken()
      const res = await fetch("/api/v1/reviews/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          assignment_id: selectedTask.id,
          scores: { novelty: reviewData.novelty, rigor: reviewData.rigor, language: reviewData.language },
          comments: reviewData.comments
        })
      })
      const result = await res.json()
      if (result.success) {
        toast.success("Review submitted. Thank you!", { id: toastId })
        setIsModalOpen(false)
        fetchTasks()
      }
    } catch (e) {
      toast.error("Submit failed. Please try again.", { id: toastId })
    }
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
              >
                <FileText className="h-4 w-4" /> Read Full Text
              </Button>
              
              <Button
                onClick={() => { setIsModalOpen(true); setSelectedTask(task); }}
                size="sm"
                className="gap-2"
              >
                <Star className="h-4 w-4" /> Start Review
              </Button>
            </div>

            {isModalOpen && selectedTask?.id === task.id && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="absolute inset-0 bg-black/50" onClick={() => setIsModalOpen(false)} />
                <div className="relative w-full max-w-[640px] rounded-3xl bg-white p-6 sm:p-8 shadow-2xl max-h-[85vh] overflow-y-auto">
                  <div className="mb-6">
                    <h4 className="font-serif text-2xl">Structured Peer Review</h4>
                    <p className="text-sm text-slate-500">
                      Submit your professional assessment for &quot;{task.manuscripts?.title}&quot;
                    </p>
                  </div>

                  <div className="py-2 space-y-6 sm:space-y-8">
                    {/* Novelty Score */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <Label className="font-semibold text-slate-700">Novelty & Originality</Label>
                        <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.novelty}/5</span>
                      </div>
                      <input type="range" min="1" max="5" value={reviewData.novelty} onChange={(e) => setReviewReviewData({...reviewData, novelty: parseInt(e.target.value)})} className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>

                    {/* Technical Rigor */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <Label className="font-semibold text-slate-700">Technical Rigor</Label>
                        <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.rigor}/5</span>
                      </div>
                      <input type="range" min="1" max="5" value={reviewData.rigor} onChange={(e) => setReviewReviewData({...reviewData, rigor: parseInt(e.target.value)})} className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>

                    {/* Language Quality */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <Label className="font-semibold text-slate-700">Language Quality</Label>
                        <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.language}/5</span>
                      </div>
                      <input type="range" min="1" max="5" value={reviewData.language} onChange={(e) => setReviewReviewData({...reviewData, language: parseInt(e.target.value)})} className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>

                    <div className="space-y-3">
                      <Label className="font-semibold text-slate-700">Review Comments</Label>
                      <textarea
                        placeholder="Provide detailed feedback for the authors..."
                        className="min-h-[140px] sm:min-h-[160px] w-full rounded-2xl border border-slate-200 p-3 focus:ring-2 focus:ring-blue-500"
                        value={reviewData.comments}
                        onChange={(e) => setReviewReviewData({...reviewData, comments: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="mt-8 flex flex-col-reverse sm:flex-row justify-end gap-3">
                    <Button
                      onClick={() => setIsModalOpen(false)}
                      variant="ghost"
                      className="w-full sm:w-auto"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSubmitReview}
                      className="w-full sm:w-auto"
                    >
                      Submit Decision <Send className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            )}
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
    </div>
  )
}
