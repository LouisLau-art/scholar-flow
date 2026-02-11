'use client'

import { useState, useEffect } from 'react';
import { User, UserRole } from '@/types/user';
import { Loader2, AlertTriangle } from 'lucide-react';

interface UserRoleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (userId: string, newRoles: UserRole[], reason: string) => Promise<void>;
  user: User | null;
}

const ROLE_OPTIONS: Array<{ value: UserRole; label: string; helper: string }> = [
  { value: 'author', label: 'Author', helper: '投稿与修回' },
  { value: 'reviewer', label: 'Reviewer', helper: '审稿工作台与意见提交' },
  { value: 'assistant_editor', label: 'Assistant Editor', helper: 'Technical pre-check' },
  { value: 'managing_editor', label: 'Managing Editor', helper: 'Intake 与分配' },
  { value: 'editor_in_chief', label: 'Editor-in-Chief', helper: 'Academic pre-check / final decision' },
  { value: 'admin', label: 'Admin', helper: '全局管理权限' },
]

export function UserRoleDialog({ isOpen, onClose, onConfirm, user }: UserRoleDialogProps) {
  const [selectedRoles, setSelectedRoles] = useState<UserRole[]>(['author']);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && user) {
      const roles = (user.roles || []).filter(Boolean) as UserRole[]
      setSelectedRoles(roles.length > 0 ? roles : ['author'])
      setReason('');
      setError(null);
    }
  }, [isOpen, user]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedRoles.length === 0) {
      setError('Please select at least one role.')
      return
    }
    if (reason.trim().length < 10) {
      setError('Reason must be at least 10 characters long.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(user.id, selectedRoles, reason);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleRole = (role: UserRole) => {
    setSelectedRoles((prev) => {
      if (prev.includes(role)) {
        return prev.filter((r) => r !== role)
      }
      return [...prev, role]
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-background rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-border">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-muted/50">
          <h3 className="font-bold text-lg text-foreground">Edit User Roles</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4">
            <p className="text-sm text-primary/80"><span className="font-semibold">User:</span> {user.full_name} ({user.email})</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Roles (Multi-select)</label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {ROLE_OPTIONS.map((role) => {
                const checked = selectedRoles.includes(role.value)
                return (
                  <label
                    key={role.value}
                    className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                      checked ? 'border-primary bg-primary/5' : 'border-input'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleRole(role.value)}
                      className="mt-0.5 h-4 w-4"
                    />
                    <span>
                      <span className="block font-medium text-foreground">{role.label}</span>
                      <span className="block text-xs text-muted-foreground">{role.helper}</span>
                    </span>
                  </label>
                )
              })}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Reason <span className="text-destructive">*</span></label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          {error && <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2"><AlertTriangle className="h-4 w-4" />{error}</div>}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-foreground bg-background border border-input rounded-md hover:bg-muted">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 flex items-center gap-2">{isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />} Confirm</button>
          </div>
        </form>
      </div>
    </div>
  );
}
