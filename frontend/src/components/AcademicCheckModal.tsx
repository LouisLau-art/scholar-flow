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
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!decision) return;
    setIsSubmitting(true);
    try {
      await editorService.submitAcademicCheck(manuscriptId, decision);
      onSuccess();
      onClose();
    } catch (error) {
      console.error("Failed to submit academic check", error);
      alert("Failed to submit check");
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

        <div className="flex justify-end gap-2">
          <button 
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
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
