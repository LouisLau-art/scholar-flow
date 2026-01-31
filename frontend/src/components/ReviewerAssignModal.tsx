import { useState, useEffect } from 'react'
import { X, Search, Users, Check, UserPlus } from 'lucide-react'
import { InviteReviewerDialog } from '@/components/admin/InviteReviewerDialog'
import { adminUserService } from '@/services/admin/userService'
import { toast } from 'sonner'

interface Reviewer {
// ...
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
  
  // Invite Dialog
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false)

  useEffect(() => {
// ...
  const handleAssign = () => {
    if (selectedReviewer) {
      onAssign(selectedReviewer)
      onClose()
      setSelectedReviewer(null)
    }
  }

  const handleInviteConfirm = async (email: string, fullName: string) => {
    try {
      const newUser = await adminUserService.inviteReviewer({
        email,
        full_name: fullName,
        manuscript_id: manuscriptId
      })
      toast.success('Reviewer invited successfully!')
      // Refresh list or select new user
      fetchReviewers()
      // Optionally pre-select the new user if we can find them
    } catch (error) {
      console.error('Invite failed:', error)
      throw error // Let dialog handle error
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="reviewer-modal">
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
            <div className="mb-6 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search reviewers by name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  data-testid="reviewer-search"
                />
              </div>
              <button
                onClick={() => setIsInviteDialogOpen(true)}
                className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium"
              >
                <UserPlus className="h-4 w-4" />
                Invite New
              </button>
            </div>

            {isLoading ? (
// ...
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
              data-testid="reviewer-assign"
            >
              Assign Reviewer
            </button>
          </div>
        </div>
      </div>

      <InviteReviewerDialog 
        isOpen={isInviteDialogOpen} 
        onClose={() => setIsInviteDialogOpen(false)} 
        onConfirm={handleInviteConfirm}
      />
    </>
  )
}
