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
    console.log('Sending invitation email to', id)
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
        <Mail className="h-5 w-5 text-blue-600" /> AI Recommendations
      </h3>

      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
        {recommendations.length > 0 ? (
          recommendations.map((rec) => (
            <div key={rec.reviewer_id} className="flex items-center justify-between p-4 hover:bg-slate-50">
              <div>
                <p className="font-medium text-slate-900">{rec.email}</p>
                <p className="text-xs text-slate-500">Match Score: {(rec.score * 100).toFixed(1)}%</p>
              </div>
              
              <button 
                onClick={() => handleInvite(rec.reviewer_id)}
                disabled={invitedIds.includes(rec.reviewer_id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                  invitedIds.includes(rec.reviewer_id) 
                    ? 'bg-green-50 text-green-700' 
                    : 'bg-slate-900 text-white hover:bg-blue-700'
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
          <div className="p-8 text-center text-slate-400">
            <AlertTriangle className="mx-auto h-8 w-8 mb-2" />
            <p>No highly matching reviewers found. Try manual search.</p>
          </div>
        )}
      </div>
    </div>
  )
}
