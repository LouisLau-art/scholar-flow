'use client'

import { useState } from 'react';
import { UserRole } from '@/types/user';
import { Loader2, AlertTriangle, Mail } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface CreateUserDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (email: string, fullName: string, role: UserRole) => Promise<void>;
}

export function CreateUserDialog({ isOpen, onClose, onConfirm }: CreateUserDialogProps) {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<UserRole>('author');
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
      await onConfirm(email, fullName, role);
      // Reset form
      setEmail('');
      setFullName('');
      setRole('author');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-background rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-border">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-muted/50">
          <h3 className="font-bold text-lg text-foreground">Invite New Member</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4 flex items-start gap-3">
            <Mail className="h-5 w-5 text-primary mt-0.5" />
            <p className="text-sm text-primary/80">
              An account will be created and an email notification with login credentials will be sent to the user.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email Address <span className="text-destructive">*</span></label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="colleague@example.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Full Name <span className="text-destructive">*</span></label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-md border border-input bg-background py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="John Doe"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Role <span className="text-destructive">*</span></label>
            <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="author">Author</SelectItem>
                <SelectItem value="reviewer">Reviewer</SelectItem>
                <SelectItem value="assistant_editor">Assistant Editor</SelectItem>
                <SelectItem value="production_editor">Production Editor</SelectItem>
                <SelectItem value="managing_editor">Managing Editor</SelectItem>
                <SelectItem value="editor_in_chief">Editor-in-Chief</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-foreground bg-background border border-input rounded-md hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
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
