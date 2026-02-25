import React, { useState } from 'react';
import { editorService } from '../services/editorService';

interface AcademicCheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  manuscriptId: string;
  onSuccess: () => void;
}

export const AcademicCheckModal: React.FC<AcademicCheckModalProps> = ({ isOpen, onClose, manuscriptId, onSuccess }) => {
  const [decision, setDecision] = useState<string>('');
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!decision) return;
    setIsSubmitting(true);
    setError('');
    try {
      await editorService.submitAcademicCheck(manuscriptId, decision as 'review' | 'decision_phase', comment || undefined);
      onSuccess();
      onClose();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to submit check');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Academic Pre-check Decision</h2>
        
        <div className="mb-4 space-y-2">
          <label className="flex items-center space-x-2">
            <input 
              type="radio" 
              name="decision" 
              value="review" 
              checked={decision === 'review'}
              onChange={(e) => setDecision(e.target.value)}
            />
            <span>Send to External Review</span>
          </label>
          <label className="flex items-center space-x-2">
            <input 
              type="radio" 
              name="decision" 
              value="decision_phase" 
              checked={decision === 'decision_phase'}
              onChange={(e) => setDecision(e.target.value)}
            />
            <span>Proceed to Decision Phase (Reject/Revision)</span>
          </label>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Comment (Optional)</label>
          <textarea
            className="w-full border rounded p-2 min-h-[96px]"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={2000}
            disabled={isSubmitting}
            placeholder="Add context for review/decision route..."
          />
          {error ? <div className="mt-2 text-xs text-red-600">{error}</div> : null}
        </div>

        <div className="flex justify-end gap-2">
          <button 
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button 
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
            onClick={handleSubmit}
            disabled={!decision || isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  );
};
