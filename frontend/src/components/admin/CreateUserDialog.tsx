'use client'

import { useState } from 'react';
import { UserRole } from '@/types/user';
import { Loader2, AlertTriangle, Mail } from 'lucide-react';
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
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="max-w-md p-0 overflow-hidden">
        <DialogHeader className="border-b border-border bg-muted/50 px-6 py-4">
          <DialogTitle>Invite New Member</DialogTitle>
          <DialogDescription>
            Create account and send login credentials to the user.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div className="bg-primary/5 p-3 rounded-md border border-primary/10 mb-4 flex items-start gap-3">
            <Mail className="h-5 w-5 text-primary mt-0.5" />
            <p className="text-sm text-primary/80">
              An account will be created and an email notification with login credentials will be sent to the user.
            </p>
          </div>

          <div>
            <Label htmlFor="create-user-email" className="mb-1 block text-foreground">
              Email Address <span className="text-destructive">*</span>
            </Label>
            <Input
              id="create-user-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@example.com"
              required
            />
          </div>

          <div>
            <Label htmlFor="create-user-full-name" className="mb-1 block text-foreground">
              Full Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="create-user-full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="John Doe"
              required
            />
          </div>

          <div>
            <Label className="mb-1 block text-foreground">
              Role <span className="text-destructive">*</span>
            </Label>
            <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="author">Author</SelectItem>
                <SelectItem value="reviewer">Reviewer</SelectItem>
                <SelectItem value="owner">Owner</SelectItem>
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

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Send Invitation
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
