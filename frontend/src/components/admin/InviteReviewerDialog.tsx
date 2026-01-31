'use client'

import { useState } from 'react';
import { Loader2, AlertTriangle, Send } from 'lucide-react';

interface InviteReviewerDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (email: string, fullName: string) => Promise<void>;
}

export function InviteReviewerDialog({ isOpen, onClose, onConfirm }: InviteReviewerDialogProps) {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !fullName) {
      setError('Please fill in all fields.');
      return;
    }

    if (!email.includes('@')) {
        setError('Invalid email address.');
        return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onConfirm(email, fullName);
      setEmail('');
      setFullName('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite reviewer');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h3 className="font-bold text-lg text-slate-900">Invite New Reviewer</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-blue-50 p-3 rounded-md border border-blue-100 mb-4 flex items-start gap-3">
            <Send className="h-5 w-5 text-blue-600 mt-0.5" />
            <p className="text-sm text-blue-800">
              The user will receive a Magic Link to log in and access the review dashboard immediately.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email Address <span className="text-red-500">*</span></label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="reviewer@university.edu"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Full Name <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-md border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Dr. Jane Doe"
              required
            />
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
              Send Invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
