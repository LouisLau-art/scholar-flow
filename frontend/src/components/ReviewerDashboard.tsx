"use client"

import { useState, useEffect } from "react"
import { Star, FileText, Send } from "lucide-react"
import { toast } from "sonner"
import Link from "next/link"
import { authService } from "@/services/auth"

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
              <Link href={`/articles/${task.manuscript_id}`}>
                <button className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                  <FileText className="h-4 w-4 mr-2" /> View PDF
                </button>
              </Link>
              
              <button
                onClick={() => { setIsModalOpen(true); setSelectedTask(task); }}
                className="bg-slate-900 rounded-xl px-6 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              >
                <Star className="h-4 w-4 mr-2" /> Start Review
              </button>
            </div>

            {isModalOpen && selectedTask?.id === task.id && (
              <div className="fixed inset-0 z-50 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/50" onClick={() => setIsModalOpen(false)} />
                <div className="relative w-full max-w-[600px] rounded-3xl bg-white p-8 shadow-2xl">
                  <div className="mb-6">
                    <h4 className="font-serif text-2xl">Structured Peer Review</h4>
                    <p className="text-sm text-slate-500">
                      Submit your professional assessment for &quot;{task.manuscripts?.title}&quot;
                    </p>
                  </div>

                  <div className="py-2 space-y-8">
                    {/* Novelty Score */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-slate-700">Novelty & Originality</span>
                        <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.novelty}/5</span>
                      </div>
                      <input type="range" min="1" max="5" value={reviewData.novelty} onChange={(e) => setReviewReviewData({...reviewData, novelty: parseInt(e.target.value)})} className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>

                    {/* Technical Rigor */}
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-slate-700">Technical Rigor</span>
                        <span className="text-blue-600 font-mono font-bold text-xl">{reviewData.rigor}/5</span>
                      </div>
                      <input type="range" min="1" max="5" value={reviewData.rigor} onChange={(e) => setReviewReviewData({...reviewData, rigor: parseInt(e.target.value)})} className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>

                    <div className="space-y-3">
                      <span className="font-bold text-slate-700">Review Comments</span>
                      <textarea
                        placeholder="Provide detailed feedback for the authors..."
                        className="min-h-[150px] w-full rounded-2xl border border-slate-200 p-3 focus:ring-2 focus:ring-blue-500"
                        value={reviewData.comments}
                        onChange={(e) => setReviewReviewData({...reviewData, comments: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="mt-8 flex justify-end gap-3">
                    <button
                      onClick={() => setIsModalOpen(false)}
                      className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitReview}
                      className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-8 py-2 text-sm font-bold"
                    >
                      Submit Decision <Send className="ml-2 h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
