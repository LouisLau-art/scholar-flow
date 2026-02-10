import React, { useState } from 'react';
import { editorService } from '../services/editorService';
import { getAssistantEditors, peekAssistantEditorsCache, type AssistantEditorOption } from '@/services/assistantEditorsCache';

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
  const [aes, setAes] = useState<AssistantEditorOption[]>([]);
  const [error, setError] = useState<string>('');

  React.useEffect(() => {
    let mounted = true;
    if (!isOpen) {
      setSelectedAE('');
      setError('');
      return () => {
        mounted = false;
      };
    }

    const cached = peekAssistantEditorsCache();
    if (cached && cached.length) {
      setAes(cached);
    }

    async function loadAEs() {
      const hasCached = Boolean(cached && cached.length);
      // 只有“完全无缓存”时才阻塞下拉；有缓存就允许立即选择
      setIsLoadingAEs(!hasCached);
      setError('');
      try {
        const rows = await getAssistantEditors();
        if (mounted) {
          setAes(rows);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load assistant editors');
          if (!cached?.length) setAes([]);
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

  if (!isOpen) return null;

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
            disabled={isSubmitting || (isLoadingAEs && aes.length === 0)}
          >
            <option value="">
              {isLoadingAEs && aes.length === 0 ? '-- Loading assistant editors... --' : '-- Select --'}
            </option>
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
