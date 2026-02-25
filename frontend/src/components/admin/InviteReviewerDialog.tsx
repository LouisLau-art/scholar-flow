'use client'

import { useState } from 'react';
import { Loader2, AlertTriangle, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

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
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="max-w-md p-0 overflow-hidden">
        <DialogHeader className="border-b border-border bg-muted/50 px-6 py-4">
          <DialogTitle>Invite New Reviewer</DialogTitle>
          <DialogDescription>
            Send a magic-link invitation for reviewer workspace access.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4 flex items-start gap-3">
            <Send className="h-5 w-5 text-primary mt-0.5" />
            <p className="text-sm text-primary/80">The user will receive a Magic Link to access the review dashboard.</p>
          </div>
          <div>
            <Label htmlFor="invite-reviewer-email" className="mb-1 block text-foreground">
              Email <span className="text-destructive">*</span>
            </Label>
            <Input
              id="invite-reviewer-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="reviewer@example.edu"
              required
            />
          </div>
          <div>
            <Label htmlFor="invite-reviewer-full-name" className="mb-1 block text-foreground">
              Full Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="invite-reviewer-full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Dr. Jane Doe"
              required
            />
          </div>
          {error && <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2"><AlertTriangle className="h-4 w-4" />{error}</div>}
          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />} Send Invite
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
