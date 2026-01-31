'use client'

import { useState, useEffect } from 'react';
import { User, UserRole } from '@/types/user';
import { Loader2, AlertTriangle } from 'lucide-react';

interface UserRoleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (userId: string, newRole: UserRole, reason: string) => Promise<void>;
  user: User | null;
}

export function UserRoleDialog({ isOpen, onClose, onConfirm, user }: UserRoleDialogProps) {
  const [role, setRole] = useState<UserRole>('author');
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && user) {
      setRole(user.roles[0] || 'author');
      setReason('');
      setError(null);
    }
  }, [isOpen, user]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 10) {
      setError('Reason must be at least 10 characters long.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(user.id, role, reason);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-background rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-border">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-muted/50">
          <h3 className="font-bold text-lg text-foreground">Change User Role</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4">
            <p className="text-sm text-primary/80"><span className="font-semibold">User:</span> {user.full_name} ({user.email})</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">New Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value as UserRole)} className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="author">Author</option>
              <option value="reviewer">Reviewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
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