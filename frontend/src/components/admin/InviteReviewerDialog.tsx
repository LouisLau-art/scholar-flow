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
      <div className="w-full max-w-md bg-background rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-border">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-muted/50">
          <h3 className="font-bold text-lg text-foreground">Invite New Reviewer</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4 flex items-start gap-3">
            <Send className="h-5 w-5 text-primary mt-0.5" />
            <p className="text-sm text-primary/80">The user will receive a Magic Link to access the review dashboard.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email <span className="text-destructive">*</span></label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="reviewer@example.edu" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Full Name <span className="text-destructive">*</span></label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Dr. Jane Doe" required />
          </div>
          {error && <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2"><AlertTriangle className="h-4 w-4" />{error}</div>}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-foreground bg-background border border-input rounded-md hover:bg-muted">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 flex items-center gap-2">{isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />} Send Invite</button>
          </div>
        </form>
      </div>
    </div>
  );
}
