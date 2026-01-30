'use client'

import { useState } from 'react'
import { CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { authService } from '@/services/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'

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
  onSubmitted?: () => void
}

export default function DecisionPanel({
  manuscriptId,
  reviewerScores = [],
  onSubmitted
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
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.')
        setIsSubmitting(false)
        return
      }
      const response = await fetch('/api/v1/editor/decision', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          manuscript_id: manuscriptId,
          decision,
          comment
        })
      })

      if (response.ok) {
        setSubmitSuccess(true)
        toast.success('Decision submitted.')
        if (onSubmitted) onSubmitted()
      } else {
        throw new Error('Submission failed')
      }
    } catch (error) {
      console.error('Failed to submit decision:', error)
      toast.error('Failed to submit decision. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitSuccess) {
    return (
      <Card className="text-center">
        <CardContent className="p-8">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
          </div>
          <h3 className="mb-2 text-xl font-semibold text-foreground">Decision Submitted!</h3>
          <p className="mb-6 text-sm text-muted-foreground">
            The manuscript decision has been successfully recorded.
          </p>
          <div className="rounded-lg bg-muted p-4">
            <div className="mb-2 flex items-center justify-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${
                  decision === "accept" ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="text-sm font-medium text-foreground">
                Decision: {decision === "accept" ? "Accepted" : "Rejected"}
              </span>
            </div>
            {comment && (
              <div className="mt-2 text-sm text-muted-foreground">
                Comment: {comment}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-6 w-6 text-primary" />
          <CardTitle>Final Decision</CardTitle>
        </div>
      </CardHeader>

      {/* Score Summary */}
      <CardContent className="space-y-6">
        <div className="rounded-lg bg-muted p-4">
          <h4 className="mb-2 text-sm font-medium text-foreground">Reviewer Score Summary</h4>
          {reviewerScores.length > 0 ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Average Overall Score:</span>
                <span className="text-lg font-semibold text-primary">
                  {averageOverallScore.toFixed(1)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Number of Reviews:</span>
                <span className="text-lg font-semibold text-primary">
                  {reviewerScores.length}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No reviewer scores available</p>
          )}
        </div>

        {/* Decision Options */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-foreground">Decision</h4>
          <RadioGroup
            value={decision ?? ""}
            onValueChange={(value) => setDecision(value as "accept" | "reject")}
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            <Label htmlFor="decision-accept" className="cursor-pointer">
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "accept"
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-accept" value="accept" className="mt-1" />
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-foreground">Accept for Publication</div>
                  <div className="text-xs text-muted-foreground">
                    The manuscript meets the quality standards and will be published
                  </div>
                </div>
              </div>
            </Label>

            <Label htmlFor="decision-reject" className="cursor-pointer">
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "reject"
                    ? "border-rose-500 bg-rose-50 text-rose-700"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-reject" value="reject" className="mt-1" />
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-foreground">Reject Manuscript</div>
                  <div className="text-xs text-muted-foreground">
                    The manuscript does not meet the quality standards
                  </div>
                </div>
              </div>
            </Label>
          </RadioGroup>
        </div>

        {/* Comment */}
        {decision && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-foreground">Decision Comment (Optional)</h4>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Enter any additional comments about this decision..."
              rows={4}
              className="w-full rounded-md border border-input bg-background p-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!decision || isSubmitting}
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Submitting...
            </>
          ) : (
            "Submit Decision"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
