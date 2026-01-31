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
      // Default to current role or first role if multiple
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

    if (role === user.roles[0]) {
      setError('Please select a different role.');
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
      <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h3 className="font-bold text-lg text-slate-900">Change User Role</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-blue-50 p-3 rounded-md border border-blue-100 mb-4">
            <p className="text-sm text-blue-800">
              <span className="font-semibold">User:</span> {user.full_name} ({user.email})
            </p>
            <p className="text-sm text-blue-800 mt-1">
              <span className="font-semibold">Current Role:</span> {user.roles.join(', ')}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">New Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full rounded-md border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="author">Author</option>
              <option value="reviewer">Reviewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Reason for Change <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="Please explain why you are changing this user's role..."
              className="w-full rounded-md border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 mt-1">Min. 10 characters.</p>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-md">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-md hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Confirm Change
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
