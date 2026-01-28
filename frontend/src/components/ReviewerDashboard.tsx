"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Star, FileText, CheckCircle } from "lucide-react"
import { toast } from "sonner"

import { Star, FileText, CheckCircle, Send, X } from "lucide-react"
import { toast } from "sonner"
import Link from "next/link"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { Label } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"

export default function ReviewerDashboard() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<any>(null)
  const [reviewData, setReviewReviewData] = useState({ novelty: 3, rigor: 3, language: 3, comments: "" })

  const fetchTasks = async () => {
    try {
      const res = await fetch("/api/v1/reviews/my-tasks?user_id=88888888-8888-8888-8888-888888888888")
      const data = await res.json()
      setTasks(data.data || [])
    } catch (e) {
      toast.error("加载任务失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleSubmitReview = async () => {
    const toastId = toast.loading("提交评审意见中...")
    try {
      const res = await fetch("/api/v1/reviews/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assignment_id: selectedTask.id,
          scores: { novelty: reviewData.novelty, rigor: reviewData.rigor, language: reviewData.language },
          comments: reviewData.comments
        })
      })
      const result = await res.json()
      if (result.success) {
        toast.success("评审已提交，感谢您的贡献！", { id: toastId })
        setIsModalOpen(false)
        fetchTasks()
      }
    } catch (e) {
      toast.error("提交失败，请重试", { id: toastId })
    }
  }

  return (
    <div className="space-y-6">
      {/* ... 之前的 Header 代码 ... */}
      
      <div className="grid gap-4">
        {tasks.map((task) => (
          <Card key={task.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div className="space-y-1">
                <CardTitle className="text-xl font-serif">{task.manuscripts?.title}</CardTitle>
                <CardDescription className="line-clamp-2 italic">{task.manuscripts?.abstract}</CardDescription>
              </div>
              <Badge className="bg-blue-600">PENDING REVIEW</Badge>
            </CardHeader>
            <CardContent className="flex justify-end gap-3 pt-4 border-t border-slate-50">
              <Link href={`/articles/${task.manuscript_id}`}>
                <Button variant="outline" size="sm" className="rounded-xl">
                  <FileText className="h-4 w-4 mr-2" /> View PDF
                </Button>
              </Link>
              
              <Dialog open={isModalOpen && selectedTask?.id === task.id} onOpenChange={(open) => { setIsModalOpen(open); if(open) setSelectedTask(task); }}>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-slate-900 rounded-xl px-6">
                    <Star className="h-4 w-4 mr-2" /> Start Review
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[600px] rounded-3xl">
                  <DialogHeader>
                    <DialogTitle className="font-serif text-2xl">Structured Peer Review</DialogTitle>
                    <DialogDescription>Submit your professional assessment for "{task.manuscripts?.title}"</DialogDescription>
                  </DialogHeader>
                  
                  <div className="py-6 space-y-8">
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
                      <Textarea placeholder="Provide detailed feedback for the authors..." className="min-h-[150px] rounded-2xl border-slate-200 focus:ring-blue-500" value={reviewData.comments} onChange={(e) => setReviewReviewData({...reviewData, comments: e.target.value})} />
                    </div>
                  </div>

                  <DialogFooter>
                    <Button variant="ghost" onClick={() => setIsModalOpen(false)} className="rounded-xl">Cancel</Button>
                    <Button onClick={handleSubmitReview} className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-8 font-bold">
                      Submit Decision <Send className="ml-2 h-4 w-4" />
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
