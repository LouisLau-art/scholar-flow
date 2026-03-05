'use client'

import { useCallback, useEffect, useRef, useState } from 'react';
import { UserRole } from '@/types/user';
import { Loader2, AlertTriangle, Mail, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
  const submitTokenRef = useRef(0);
  const closeHandledRef = useRef(false);
  const backdropRef = useRef<HTMLButtonElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);
  const cancelBtnRef = useRef<HTMLButtonElement | null>(null);

  const handleClose = useCallback(() => {
    if (closeHandledRef.current) return;
    closeHandledRef.current = true;
    // 允许在提交中主动关闭，避免请求挂起导致弹窗锁死。
    submitTokenRef.current += 1;
    setIsSubmitting(false);
    setError(null);
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      closeHandledRef.current = false;
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        handleClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleClose, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onNativeClose = (event: Event) => {
      event.preventDefault();
      handleClose();
    };

    const closeTargets = [backdropRef.current, closeBtnRef.current, cancelBtnRef.current];
    closeTargets.forEach((element) => element?.addEventListener('click', onNativeClose));

    return () => {
      closeTargets.forEach((element) => element?.removeEventListener('click', onNativeClose));
    };
  }, [handleClose, isOpen]);

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
    const submitToken = submitTokenRef.current + 1;
    submitTokenRef.current = submitToken;

    try {
      await onConfirm(email, fullName, role);
      if (submitTokenRef.current !== submitToken) return;
      // Reset form
      setEmail('');
      setFullName('');
      setRole('author');
      handleClose();
    } catch (err) {
      if (submitTokenRef.current !== submitToken) return;
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      if (submitTokenRef.current !== submitToken) return;
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <button
        ref={backdropRef}
        type="button"
        aria-label="Dismiss modal"
        className="absolute inset-0 bg-black/70"
        onClick={handleClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Invite New Member"
        className="relative z-[81] w-full max-w-md overflow-hidden rounded-lg border border-border bg-background shadow-lg"
      >
        <div className="border-b border-border bg-muted/50 px-6 py-4">
          <h2 className="text-lg font-semibold leading-none tracking-tight">Invite New Member</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Create account and send login credentials to the user.
          </p>
          <Button
            ref={closeBtnRef}
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100"
            aria-label="Close"
            onClick={handleClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

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

          <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-2">
            <Button
              ref={cancelBtnRef}
              type="button"
              variant="outline"
              onClick={handleClose}
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
          </div>
        </form>
      </div>
    </div>
  );
}
