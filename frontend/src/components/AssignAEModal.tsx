import React, { useState } from 'react';
import { editorService } from '../services/editorService';
import { getAssistantEditors, peekAssistantEditorsCache, type AssistantEditorOption } from '@/services/assistantEditorsCache';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';

interface AssignAEModalProps {
  isOpen: boolean;
  onClose: () => void;
  manuscriptId: string;
  onAssignSuccess: () => void;
}

export const AssignAEModal: React.FC<AssignAEModalProps> = ({ isOpen, onClose, manuscriptId, onAssignSuccess }) => {
  const [selectedAE, setSelectedAE] = useState('');
  const [searchText, setSearchText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingAEs, setIsLoadingAEs] = useState(false);
  const [aes, setAes] = useState<AssistantEditorOption[]>([]);
  const [error, setError] = useState<string>('');

  React.useEffect(() => {
    let mounted = true;
    if (!isOpen) {
      setSelectedAE('');
      setSearchText('');
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
      await editorService.assignAE(manuscriptId, selectedAE, {
        // 中文注释:
        // Intake 页是 ME “通过并分配 AE”入口：默认直接发起外审并兜底绑定 owner。
        startExternalReview: true,
        bindOwnerIfEmpty: true,
      });
      onAssignSuccess();
      onClose();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to assign AE');
    } finally {
      setIsSubmitting(false);
    }
  };

  const normalizedSearch = searchText.trim().toLowerCase();
  const filteredAes = normalizedSearch
    ? aes.filter((ae) => {
        const name = String(ae.full_name || '').toLowerCase();
        const email = String(ae.email || '').toLowerCase();
        return name.includes(normalizedSearch) || email.includes(normalizedSearch) || ae.id.toLowerCase().includes(normalizedSearch);
      })
    : aes;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Assign Assistant Editor</h2>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Search AE</label>
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="输入姓名或邮箱过滤"
              className="pl-9"
              disabled={isSubmitting}
            />
          </div>

          <label className="block text-sm font-medium text-gray-700 mb-1">Select AE</label>
          <Select
            value={selectedAE || '__empty'}
            onValueChange={(value) => setSelectedAE(value === '__empty' ? '' : value)}
            disabled={isSubmitting}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={isLoadingAEs && aes.length === 0 ? '-- Loading assistant editors... --' : '-- Select --'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__empty">{isLoadingAEs && aes.length === 0 ? '-- Loading assistant editors... --' : '-- Select --'}</SelectItem>
              {filteredAes.map(ae => (
                <SelectItem key={ae.id} value={ae.id}>
                  {ae.full_name || ae.email || ae.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {!isLoadingAEs && filteredAes.length === 0 ? (
            <div className="mt-2 text-xs text-gray-500">没有匹配的 AE，请调整搜索关键词。</div>
          ) : null}
          {isLoadingAEs ? <div className="mt-2 text-xs text-gray-500">Loading assistant editors...</div> : null}
          {error ? <div className="mt-2 text-xs text-red-600">{error}</div> : null}
          <div className="mt-3 rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
            分配后将自动：1) 进入 <code>under_review</code>；2) 若 owner 为空则绑定为当前 ME。
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAssign}
            disabled={!selectedAE || isSubmitting || isLoadingAEs}
          >
            {isSubmitting ? 'Assigning...' : 'Assign'}
          </Button>
        </div>
      </div>
    </div>
  );
};
