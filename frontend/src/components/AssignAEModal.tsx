import React, { useState } from 'react';
import { editorService } from '../services/editorService';

interface AssignAEModalProps {
  isOpen: boolean;
  onClose: () => void;
  manuscriptId: string;
  onAssignSuccess: () => void;
}

export const AssignAEModal: React.FC<AssignAEModalProps> = ({ isOpen, onClose, manuscriptId, onAssignSuccess }) => {
  const [selectedAE, setSelectedAE] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock AE list - in real app, fetch from API
  const mockAEs = [
    { id: 'ae-1', name: 'Alice Editor' },
    { id: 'ae-2', name: 'Bob Editor' },
  ];

  if (!isOpen) return null;

  const handleAssign = async () => {
    if (!selectedAE) return;
    setIsSubmitting(true);
    try {
      await editorService.assignAE(manuscriptId, selectedAE);
      onAssignSuccess();
      onClose();
    } catch (error) {
      console.error("Failed to assign AE", error);
      alert("Failed to assign AE");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Assign Assistant Editor</h2>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Select AE</label>
          <select 
            className="w-full border rounded p-2"
            value={selectedAE}
            onChange={(e) => setSelectedAE(e.target.value)}
          >
            <option value="">-- Select --</option>
            {mockAEs.map(ae => (
              <option key={ae.id} value={ae.id}>{ae.name}</option>
            ))}
          </select>
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
            onClick={handleAssign}
            disabled={!selectedAE || isSubmitting}
          >
            {isSubmitting ? 'Assigning...' : 'Assign'}
          </button>
        </div>
      </div>
    </div>
  );
};
