'use client'

import { useState, useEffect } from 'react'
import { X, Search, Users, Check } from 'lucide-react'

interface Reviewer {
  id: string
  name: string
  email: string
  affiliation: string
  expertise: string[]
  review_count: number
}

interface ReviewerAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerId: string) => void
  manuscriptId?: string
}

export default function ReviewerAssignModal({
  isOpen,
  onClose,
  onAssign,
  manuscriptId
}: ReviewerAssignModalProps) {
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedReviewer, setSelectedReviewer] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchReviewers()
    }
  }, [isOpen])

  async function fetchReviewers() {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/editor/available-reviewers')
      const data = await response.json()
      if (data.success) {
        setReviewers(data.data)
      }
    } catch (error) {
      console.error('Failed to fetch reviewers:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredReviewers = reviewers.filter(reviewer =>
    reviewer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    reviewer.affiliation.toLowerCase().includes(searchTerm.toLowerCase()) ||
    reviewer.expertise.some(exp => exp.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const handleAssign = () => {
    if (selectedReviewer) {
      onAssign(selectedReviewer)
      onClose()
      setSelectedReviewer(null)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <Users className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-bold text-slate-900">Assign Reviewer</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search reviewers by name, affiliation, or expertise..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-slate-600">Loading reviewers...</span>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredReviewers.map(reviewer => (
                <div
                  key={reviewer.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedReviewer === reviewer.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                  onClick={() => setSelectedReviewer(reviewer.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-slate-900">
                        {reviewer.name}
                      </div>
                      <div className="text-sm text-slate-500 mt-1">
                        {reviewer.affiliation}
                      </div>
                      {reviewer.expertise.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {reviewer.expertise.slice(0, 3).map(exp => (
                            <span
                              key={exp}
                              className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded"
                            >
                              {exp}
                            </span>
                          ))}
                          {reviewer.expertise.length > 3 && (
                            <span className="text-xs text-slate-400">+{reviewer.expertise.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>
                    {selectedReviewer === reviewer.id && (
                      <Check className="h-5 w-5 text-blue-600" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-3 text-xs text-slate-400">
                    <span>Reviews: {reviewer.review_count}</span>
                  </div>
                </div>
              ))}

              {filteredReviewers.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  No reviewers found matching "{searchTerm}"
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleAssign}
            disabled={!selectedReviewer}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          >
            Assign Reviewer
          </button>
        </div>
      </div>
    </div>
  )
}