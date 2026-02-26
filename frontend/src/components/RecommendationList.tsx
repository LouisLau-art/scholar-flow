'use client'

import { useState } from 'react'
import { UserPlus, Mail, AlertTriangle, CheckCircle } from 'lucide-react'

interface Recommendation {
  reviewer_id: string
  email: string
  score: number
}

export default function RecommendationList() {
  /**
   * 审稿人推荐列表组件
   * 遵循章程：视觉锁定深蓝系，优雅降级
   * 落实 Spec：支持手动邀请与异常（零结果）处理
   */
  const [recommendations, setRecommendations] = useState<Recommendation[]>([
    { reviewer_id: 'r-001', email: 'expert@university.edu', score: 0.85 },
    { reviewer_id: 'r-002', email: 'scholar@research.org', score: 0.42 }
  ])
  const [invitedIds, setInvitedIds] = useState<string[]>([])

  const handleInvite = (id: string) => {
    setInvitedIds([...invitedIds, id])
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
        <Mail className="h-5 w-5 text-primary" /> AI Recommendations
      </h3>

      <div className="divide-y divide-border/60 rounded-lg border border-border bg-card">
        {recommendations.length > 0 ? (
          recommendations.map((rec) => (
            <div key={rec.reviewer_id} className="flex items-center justify-between p-4 hover:bg-muted/40">
              <div>
                <p className="font-medium text-foreground">{rec.email}</p>
                <p className="text-xs text-muted-foreground">Match Score: {(rec.score * 100).toFixed(1)}%</p>
              </div>
              
              <button 
                onClick={() => handleInvite(rec.reviewer_id)}
                disabled={invitedIds.includes(rec.reviewer_id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                  invitedIds.includes(rec.reviewer_id) 
                    ? 'bg-green-50 text-green-700' 
                    : 'bg-foreground text-primary-foreground hover:bg-primary/90'
                }`}
              >
                {invitedIds.includes(rec.reviewer_id) ? (
                  <><CheckCircle className="h-4 w-4" /> Invited</>
                ) : (
                  <><UserPlus className="h-4 w-4" /> Send Invite</>
                )}
              </button>
            </div>
          ))
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            <AlertTriangle className="mx-auto h-8 w-8 mb-2" />
            <p>No highly matching reviewers found. Try manual search.</p>
          </div>
        )}
      </div>
    </div>
  )
}
