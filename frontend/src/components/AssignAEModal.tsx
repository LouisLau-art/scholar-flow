import React, { useState } from 'react';
import { editorService } from '../services/editorService';
import { getAssistantEditors, peekAssistantEditorsCache, type AssistantEditorOption } from '@/services/assistantEditorsCache';
import { EditorApi } from '@/services/editorApi';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Search } from 'lucide-react';

type InternalStaffOption = { id: string; email?: string | null; full_name?: string | null; roles?: string[] | null };

interface AssignAEModalProps {
  isOpen: boolean;
  onClose: () => void;
  manuscriptId: string;
  onAssignSuccess: () => void;
}

export const AssignAEModal: React.FC<AssignAEModalProps> = ({ isOpen, onClose, manuscriptId, onAssignSuccess }) => {
  const [selectedAE, setSelectedAE] = useState('');
  const [searchText, setSearchText] = useState('');
  const [selectedOwner, setSelectedOwner] = useState('');
  const [ownerSearchText, setOwnerSearchText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingAEs, setIsLoadingAEs] = useState(false);
  const [aes, setAes] = useState<AssistantEditorOption[]>([]);
  const [isLoadingOwners, setIsLoadingOwners] = useState(false);
  const [owners, setOwners] = useState<InternalStaffOption[]>([]);
  const [error, setError] = useState<string>('');

  React.useEffect(() => {
    let mounted = true;
    if (!isOpen) {
      setSelectedAE('');
      setSearchText('');
      setSelectedOwner('');
      setOwnerSearchText('');
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

    async function loadOwners() {
      setIsLoadingOwners(true);
      try {
        const res = await EditorApi.listInternalStaff();
        if (!mounted) return;
        if (res?.success) {
          const rows = Array.isArray(res?.data) ? (res.data as InternalStaffOption[]) : [];
          // 体验优化：把 owner 角色置顶（其余保持字母序）
          rows.sort((a, b) => {
            const aRoles = Array.isArray(a.roles) ? a.roles.map((r) => String(r).toLowerCase()) : [];
            const bRoles = Array.isArray(b.roles) ? b.roles.map((r) => String(r).toLowerCase()) : [];
            const aOwner = aRoles.includes('owner');
            const bOwner = bRoles.includes('owner');
            if (aOwner !== bOwner) return aOwner ? -1 : 1;
            const aName = String(a.full_name || a.email || '').toLowerCase();
            const bName = String(b.full_name || b.email || '').toLowerCase();
            return aName.localeCompare(bName);
          });
          setOwners(rows);
        } else {
          setOwners([]);
        }
      } catch {
        if (mounted) setOwners([]);
      } finally {
        if (mounted) setIsLoadingOwners(false);
      }
    }
    loadOwners();
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
        // Intake 页是 ME “通过并分配 AE”入口：默认直接发起外审。
        startExternalReview: true,
        // 若未显式选择 Owner，则兜底绑定为当前 ME（开发阶段快速闭环）。
        bindOwnerIfEmpty: !selectedOwner,
        ownerId: selectedOwner || undefined,
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

  const normalizedOwnerSearch = ownerSearchText.trim().toLowerCase();
  const filteredOwners = normalizedOwnerSearch
    ? owners.filter((u) => {
        const name = String(u.full_name || '').toLowerCase();
        const email = String(u.email || '').toLowerCase();
        return name.includes(normalizedOwnerSearch) || email.includes(normalizedOwnerSearch) || String(u.id || '').toLowerCase().includes(normalizedOwnerSearch);
      })
    : owners;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Assistant Editor</DialogTitle>
          <DialogDescription>
            Assign AE and optional owner for this manuscript.
          </DialogDescription>
        </DialogHeader>

        <div className="mb-4">
          <label htmlFor="assign-ae-search" className="block text-sm font-medium text-gray-700 mb-1">Search AE</label>
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              id="assign-ae-search"
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
              <SelectValue placeholder={isLoadingAEs && aes.length === 0 ? '-- Loading assistant editors… --' : '-- Select --'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__empty">{isLoadingAEs && aes.length === 0 ? '-- Loading assistant editors… --' : '-- Select --'}</SelectItem>
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
          {isLoadingAEs ? <div className="mt-2 text-xs text-gray-500">Loading assistant editors…</div> : null}
          {error ? <div className="mt-2 text-xs text-red-600">{error}</div> : null}
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            分配后将自动进入 <code>under_review</code>。Owner 可选：不选则默认绑定为当前 ME（仅开发/UAT 提速）。
          </div>
        </div>

        <div className="mb-4">
          <label htmlFor="assign-owner-search" className="block text-sm font-medium text-gray-700 mb-1">Select Owner (Optional)</label>
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              id="assign-owner-search"
              value={ownerSearchText}
              onChange={(e) => setOwnerSearchText(e.target.value)}
              placeholder="输入姓名或邮箱过滤 Owner"
              className="pl-9"
              disabled={isSubmitting}
            />
          </div>
          <Select
            value={selectedOwner || '__empty'}
            onValueChange={(value) => setSelectedOwner(value === '__empty' ? '' : value)}
            disabled={isSubmitting || isLoadingOwners}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={isLoadingOwners && owners.length === 0 ? '-- Loading owners… --' : '-- Optional --'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__empty">{isLoadingOwners && owners.length === 0 ? '-- Loading owners… --' : '-- Optional --'}</SelectItem>
              {filteredOwners.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.full_name || u.email || u.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
            {isSubmitting ? 'Assigning…' : 'Assign'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
