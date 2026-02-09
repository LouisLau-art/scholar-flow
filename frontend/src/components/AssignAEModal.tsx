import React, { useState } from 'react';
import { editorService } from '../services/editorService';
import { EditorApi } from '@/services/editorApi';

interface AssignAEModalProps {
  isOpen: boolean;
  onClose: () => void;
  manuscriptId: string;
  onAssignSuccess: () => void;
}

export const AssignAEModal: React.FC<AssignAEModalProps> = ({ isOpen, onClose, manuscriptId, onAssignSuccess }) => {
  const [selectedAE, setSelectedAE] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingAEs, setIsLoadingAEs] = useState(false);
  const [aes, setAes] = useState<Array<{ id: string; full_name?: string | null; email?: string | null }>>([]);
  const [error, setError] = useState<string>('');

  if (!isOpen) return null;

  React.useEffect(() => {
    let mounted = true;
    async function loadAEs() {
      setIsLoadingAEs(true);
      setError('');
      try {
        const res = await EditorApi.listAssistantEditors();
        if (!res?.success) {
          throw new Error(res?.detail || res?.message || 'Failed to load assistant editors');
        }
        if (mounted) {
          setAes((res.data || []) as Array<{ id: string; full_name?: string | null; email?: string | null }>);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load assistant editors');
          setAes([]);
        }
      } finally {
        if (mounted) setIsLoadingAEs(false);
      }
    }
    loadAEs();
    return () => {
      mounted = false;
    };
  }, [isOpen]);

  const handleAssign = async () => {
    if (!selectedAE) return;
    setIsSubmitting(true);
    setError('');
    try {
      await editorService.assignAE(manuscriptId, selectedAE);
      onAssignSuccess();
      onClose();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to assign AE');
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
            disabled={isLoadingAEs || isSubmitting}
          >
            <option value="">-- Select --</option>
            {aes.map(ae => (
              <option key={ae.id} value={ae.id}>{ae.full_name || ae.email || ae.id}</option>
            ))}
          </select>
          {isLoadingAEs ? <div className="mt-2 text-xs text-gray-500">Loading assistant editors...</div> : null}
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
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            onClick={handleAssign}
            disabled={!selectedAE || isSubmitting || isLoadingAEs}
          >
            {isSubmitting ? 'Assigning...' : 'Assign'}
          </button>
        </div>
      </div>
    </div>
  );
};
