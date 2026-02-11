'use client'

import { User } from '@/types/user';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface UserTableProps {
  users: User[];
  isLoading: boolean;
  page: number;
  perPage: number;
  total: number;
  onPageChange: (newPage: number) => void;
  onEdit: (user: User) => void;
  onResetPassword: (user: User) => void;
}

export function UserTable({ users, isLoading, page, perPage, total, onPageChange, onEdit, onResetPassword }: UserTableProps) {
  const totalPages = Math.ceil(total / perPage);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-card">
        <p className="text-muted-foreground">No users found matching your criteria.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-hidden rounded-lg border border-border shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-muted-foreground">
          <thead className="bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-6 py-3 font-semibold">Email</th>
              <th className="px-6 py-3 font-semibold">Full Name</th>
              <th className="px-6 py-3 font-semibold">Roles</th>
              <th className="px-6 py-3 font-semibold">Joined</th>
              <th className="px-6 py-3 font-semibold">Status</th>
              <th className="px-6 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-card">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-muted/50 transition-colors">
                <td className="px-6 py-4 font-medium text-foreground">{user.email}</td>
                <td className="px-6 py-4 text-foreground">{user.full_name || '-'}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-1 flex-wrap">
                    {user.roles.map(role => (
                      <span key={role} className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                        role === 'admin' ? 'bg-destructive/10 text-destructive' :
                        role === 'editor' ? 'bg-primary/10 text-primary' :
                        role === 'reviewer' ? 'bg-secondary text-secondary-foreground' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {role}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  {user.id ? (
                    <span className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-1 text-xs font-medium ring-1 ring-inset ring-primary/20">Active</span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-muted text-muted-foreground px-2 py-1 text-xs font-medium ring-1 ring-inset ring-border">Pending</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => onEdit(user)}
                    >
                      Edit Role
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => onResetPassword(user)}
                    >
                      Reset Password
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="flex items-center justify-between border-t border-border bg-muted/30 px-6 py-3">
        <div className="text-xs text-muted-foreground">
          Showing <span className="font-medium text-foreground">{Math.min((page - 1) * perPage + 1, total)}</span> to <span className="font-medium text-foreground">{Math.min(page * perPage, total)}</span> of <span className="font-medium text-foreground">{total}</span> results
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="rounded border border-input bg-background px-3 py-1 text-xs font-medium text-foreground disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Previous
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page * perPage >= total}
            className="rounded border border-input bg-background px-3 py-1 text-xs font-medium text-foreground disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
