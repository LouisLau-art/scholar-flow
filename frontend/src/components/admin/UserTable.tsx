'use client'

import { User } from '@/types/user';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatDateLocal } from '@/lib/date-display';

interface UserTableProps {
  users: User[];
  isLoading: boolean;
  page: number;
  perPage: number;
  total: number;
  onPageChange: (newPage: number) => void;
  onPerPageChange: (newPerPage: number) => void;
  onEdit: (user: User) => void;
  onResetPassword: (user: User) => void;
}

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;

function buildVisiblePages(currentPage: number, totalPages: number): Array<number | 'ellipsis-left' | 'ellipsis-right'> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, totalPages, currentPage, currentPage - 1, currentPage + 1]);
  const sortedPages = Array.from(pages)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((a, b) => a - b);

  const visiblePages: Array<number | 'ellipsis-left' | 'ellipsis-right'> = [];
  for (const page of sortedPages) {
    const previousPage = typeof visiblePages[visiblePages.length - 1] === 'number'
      ? (visiblePages[visiblePages.length - 1] as number)
      : null;

    if (previousPage !== null && page - previousPage > 1) {
      visiblePages.push(previousPage < currentPage ? 'ellipsis-left' : 'ellipsis-right');
    }
    visiblePages.push(page);
  }

  return visiblePages;
}

export function UserTable({
  users,
  isLoading,
  page,
  perPage,
  total,
  onPageChange,
  onPerPageChange,
  onEdit,
  onResetPassword,
}: UserTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const currentPage = Math.min(Math.max(page, 1), totalPages);
  const visiblePages = buildVisiblePages(currentPage, totalPages);

  const handlePageChange = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages || nextPage === currentPage) {
      return;
    }
    onPageChange(nextPage);
  };

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
                        role === 'managing_editor' ? 'bg-primary/10 text-primary' :
                        role === 'assistant_editor' ? 'bg-indigo-100 text-indigo-700' :
                        role === 'academic_editor' ? 'bg-cyan-100 text-cyan-700' :
                        role === 'editor_in_chief' ? 'bg-purple-100 text-purple-700' :
                        role === 'owner' ? 'bg-emerald-100 text-emerald-700' :
                        role === 'production_editor' ? 'bg-amber-100 text-amber-700' :
                        role === 'reviewer' ? 'bg-secondary text-secondary-foreground' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {role}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {formatDateLocal(user.created_at)}
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
          Showing <span className="font-medium text-foreground">{Math.min((currentPage - 1) * perPage + 1, total)}</span> to <span className="font-medium text-foreground">{Math.min(currentPage * perPage, total)}</span> of <span className="font-medium text-foreground">{total}</span> results
        </div>
        <div className="flex flex-wrap items-center justify-end gap-4">
          <div className="flex items-center gap-2">
            {PAGE_SIZE_OPTIONS.map((option) => (
              <Button
                key={option}
                type="button"
                size="sm"
                variant={option === perPage ? 'default' : 'outline'}
                onClick={() => onPerPageChange(option)}
              >
                {option} / 页
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handlePageChange(1)}
              disabled={currentPage === 1}
            >
              首页
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              上一页
            </Button>
            {visiblePages.map((item, index) => {
              if (typeof item !== 'number') {
                return (
                  <span
                    key={`${item}-${index}`}
                    className="px-1 text-xs text-muted-foreground"
                  >
                    ...
                  </span>
                );
              }

              return (
                <Button
                  key={item}
                  type="button"
                  size="sm"
                  variant={item === currentPage ? 'default' : 'outline'}
                  aria-current={item === currentPage ? 'page' : undefined}
                  onClick={() => handlePageChange(item)}
                >
                  {item}
                </Button>
              );
            })}
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              下一页
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handlePageChange(totalPages)}
              disabled={currentPage === totalPages}
            >
              末页
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
