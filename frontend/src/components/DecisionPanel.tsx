'use client'

import { useState } from 'react'
import { CheckCircle2, XCircle, AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { authService } from '@/services/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

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
  const [decision, setDecision] = useState<'accept' | 'reject' | 'revision' | null>(null)
  const [revisionType, setRevisionType] = useState<'major' | 'minor' | null>(null)
  const [comment, setComment] = useState('')
  const [apcAmount, setApcAmount] = useState<number>(1500)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  const averageOverallScore = reviewerScores.length > 0
    ? reviewerScores.reduce((sum, score) => sum + score.overall_score, 0) / reviewerScores.length
    : 0

  const handleSubmit = async () => {
    if (!decision || !manuscriptId) return

    if (decision === 'revision') {
      if (!revisionType) {
        toast.error('Please select a revision type (Major or Minor).')
        return
      }
      if (!comment || comment.trim().length < 10) {
        toast.error('Please provide detailed comments for revision (min 10 chars).')
        return
      }
    }

    if (decision === 'accept') {
      if (!Number.isFinite(apcAmount) || apcAmount < 0) {
        toast.error('Please provide a valid APC amount (>= 0).')
        return
      }
    }

    setIsSubmitting(true)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.')
        setIsSubmitting(false)
        return
      }

      let endpoint = '/api/v1/editor/decision'
      let body: any = {
        manuscript_id: manuscriptId,
        decision,
        comment
      }

      if (decision === 'accept') {
        body.apc_amount = apcAmount
      }

      if (decision === 'revision') {
        endpoint = '/api/v1/editor/revisions'
        body = {
          manuscript_id: manuscriptId,
          decision_type: revisionType,
          comment
        }
          }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSubmitSuccess(true)
        if (decision === 'revision') {
          setSuccessMessage(`Revision requested (${revisionType}).`)
        } else if (decision === 'accept') {
          setSuccessMessage('Manuscript accepted for publication.')
        } else {
          setSuccessMessage('Manuscript rejected.')
        }
        toast.success('Decision recorded successfully.')
        if (onSubmitted) onSubmitted()
      } else {
        throw new Error(data.detail || data.message || 'Submission failed')
      }
    } catch (error: any) {
      console.error('Failed to submit decision:', error)
      toast.error(error.message || 'Failed to submit decision. Please try again.')
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
          <h3 className="mb-2 text-xl font-semibold text-foreground">Success!</h3>
          <p className="mb-6 text-sm text-muted-foreground">
            {successMessage}
          </p>
          <div className="rounded-lg bg-muted p-4">
            <div className="mb-2 flex items-center justify-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${
                  decision === "accept" ? "bg-emerald-500" : 
                  decision === "revision" ? "bg-amber-500" : "bg-rose-500"
                }`}
              />
              <span className="text-sm font-medium text-foreground capitalize">
                Decision: {decision === 'revision' ? `Revision (${revisionType})` : decision}
              </span>
            </div>
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
          <h4 className="text-sm font-medium text-foreground">Select Decision</h4>
          <RadioGroup
            value={decision ?? ""}
            onValueChange={(value) => setDecision(value as any)}
            className="grid grid-cols-1 gap-4"
          >
            {/* Accept */}
            <Label htmlFor="decision-accept" className="cursor-pointer">
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "accept"
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-accept" value="accept" className="mt-1" />
                <div className="space-y-3 w-full">
                  <div className="text-sm font-semibold text-foreground">Accept for Publication</div>
                  <div className="text-xs text-muted-foreground">
                    The manuscript meets all standards.
                  </div>

                  {decision === 'accept' && (
                    <div className="mt-2 rounded-lg bg-white/60 p-3 border border-emerald-100">
                      <Label htmlFor="apc-amount" className="text-xs font-semibold text-slate-700">
                        Confirm APC Amount (USD)
                      </Label>
                      <Input
                        id="apc-amount"
                        type="number"
                        min={0}
                        step={50}
                        value={String(apcAmount)}
                        onChange={(e) => setApcAmount(Number(e.target.value))}
                        className="mt-2"
                      />
                      <p className="mt-2 text-xs text-muted-foreground">
                        Publishing will be blocked until payment is received (Financial Gate).
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </Label>

            {/* Request Revision */}
            <Label htmlFor="decision-revision" className="cursor-pointer">
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "revision"
                    ? "border-amber-500 bg-amber-50 text-amber-900"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-revision" value="revision" className="mt-1" />
                <div className="space-y-3 w-full">
                  <div className="space-y-1">
                    <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      Request Revision
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Require changes from the author before acceptance.
                    </div>
                  </div>
                  
                  {/* Nested Options for Revision Type */}
                  {decision === 'revision' && (
                    <div className="mt-3 pl-2 border-l-2 border-amber-200">
                      <RadioGroup
                        value={revisionType ?? ""}
                        onValueChange={(v) => setRevisionType(v as 'major' | 'minor')}
                        className="flex gap-4"
                      >
                         <div className="flex items-center space-x-2">
                           <RadioGroupItem value="minor" id="r-minor" />
                           <Label htmlFor="r-minor">Minor Revision</Label>
                         </div>
                         <div className="flex items-center space-x-2">
                           <RadioGroupItem value="major" id="r-major" />
                           <Label htmlFor="r-major">Major Revision</Label>
                         </div>
                      </RadioGroup>
                    </div>
                  )}
                </div>
              </div>
            </Label>

            {/* Reject */}
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
                    The manuscript does not meet quality standards.
                  </div>
                </div>
              </div>
            </Label>
          </RadioGroup>
        </div>

        {/* Comment */}
        {decision && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-foreground">
              {decision === 'revision' ? 'Revision Instructions (Required)' : 'Decision Comment (Optional)'}
            </h4>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={decision === 'revision' ? "Please list the specific changes required..." : "Enter any additional comments..."}
              rows={6}
              className="w-full rounded-md border border-input bg-background p-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            {decision === 'revision' && (
              <p className="text-xs text-muted-foreground text-right">
                {comment.trim().length}/10 characters minimum
              </p>
            )}
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!decision || isSubmitting || (decision === 'revision' && (!revisionType || comment.trim().length < 10))}
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Submitting Decision...
            </>
          ) : (
            "Submit Decision"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
