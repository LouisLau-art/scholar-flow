'use client'

import { useState } from 'react'
import { CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react'

interface DecisionPanelProps {
  manuscriptId?: string
  reviewerScores?: {
    reviewer_id: string
    name: string
    overall_score: number
    technical_score: number
    clarity_score: number
    originality_score: number
    comments: string
  }[]
}

export default function DecisionPanel({
  manuscriptId,
  reviewerScores = []
}: DecisionPanelProps) {
  const [decision, setDecision] = useState<'accept' | 'reject' | null>(null)
  const [comment, setComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  const averageOverallScore = reviewerScores.length > 0
    ? reviewerScores.reduce((sum, score) => sum + score.overall_score, 0) / reviewerScores.length
    : 0

  const handleSubmit = async () => {
    if (!decision || !manuscriptId) return

    setIsSubmitting(true)
    try {
      const response = await fetch('/api/v1/editor/decision', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          manuscript_id: manuscriptId,
          decision,
          comment
        })
      })

      if (response.ok) {
        setSubmitSuccess(true)
      } else {
        throw new Error('Submission failed')
      }
    } catch (error) {
      console.error('Failed to submit decision:', error)
      alert('Failed to submit decision. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitSuccess) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <CheckCircle2 className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">Decision Submitted!</h3>
        <p className="text-slate-600 mb-6">
          The manuscript decision has been successfully recorded.
        </p>
        <div className="bg-slate-50 p-4 rounded-lg">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className={`h-2 w-2 rounded-full ${
              decision === 'accept' ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="font-medium text-slate-900">
              Decision: {decision === 'accept' ? 'Accepted' : 'Rejected'}
            </span>
          </div>
          {comment && (
            <div className="text-sm text-slate-500 mt-2">
              Comment: {comment}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <AlertCircle className="h-6 w-6 text-blue-600" />
        <h3 className="text-xl font-bold text-slate-900">Final Decision</h3>
      </div>

      {/* Score Summary */}
      <div className="bg-slate-50 p-4 rounded-lg mb-6">
        <h4 className="font-medium text-slate-900 mb-2">Reviewer Score Summary</h4>
        {reviewerScores.length > 0 ? (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-600">Average Overall Score:</span>
              <span className="text-lg font-bold text-blue-600">
                {averageOverallScore.toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-600">Number of Reviews:</span>
              <span className="text-lg font-bold text-blue-600">
                {reviewerScores.length}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No reviewer scores available</p>
        )}
      </div>

      {/* Decision Options */}
      <div className="space-y-6 mb-6">
        <div>
          <h4 className="font-medium text-slate-900 mb-3">Decision</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setDecision('accept')}
              className={`p-4 border rounded-lg flex items-center gap-3 transition-all ${
                decision === 'accept'
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <CheckCircle2 className="h-5 w-5" />
              <div>
                <div className="font-medium">Accept for Publication</div>
                <div className="text-sm text-slate-500">
                  The manuscript meets the quality standards and will be published
                </div>
              </div>
            </button>

            <button
              onClick={() => setDecision('reject')}
              className={`p-4 border rounded-lg flex items-center gap-3 transition-all ${
                decision === 'reject'
                  ? 'border-red-500 bg-red-50 text-red-700'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <XCircle className="h-5 w-5" />
              <div>
                <div className="font-medium">Reject Manuscript</div>
                <div className="text-sm text-slate-500">
                  The manuscript does not meet the quality standards
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Comment */}
        {decision && (
          <div>
            <h4 className="font-medium text-slate-900 mb-3">Decision Comment (Optional)</h4>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Enter any additional comments about this decision..."
              rows={4}
              className="w-full p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!decision || isSubmitting}
        className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Submitting...
          </>
        ) : (
          'Submit Decision'
        )}
      </button>
    </div>
  )
}