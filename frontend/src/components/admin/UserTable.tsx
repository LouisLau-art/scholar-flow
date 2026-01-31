'use client'

import { User } from '@/types/user';
import { Loader2 } from 'lucide-react';

interface UserTableProps {
  users: User[];
  isLoading: boolean;
  page: number;
  perPage: number;
  total: number;
  onPageChange: (newPage: number) => void;
  onEdit: (user: User) => void;
}

export function UserTable({ users, isLoading, page, perPage, total, onPageChange, onEdit }: UserTableProps) {
  const totalPages = Math.ceil(total / perPage);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-300">
        <p className="text-slate-500">No users found matching your criteria.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-hidden rounded-lg border border-slate-200 shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-6 py-3 font-semibold">Email</th>
              <th className="px-6 py-3 font-semibold">Full Name</th>
              <th className="px-6 py-3 font-semibold">Roles</th>
              <th className="px-6 py-3 font-semibold">Joined</th>
              <th className="px-6 py-3 font-semibold">Status</th>
              <th className="px-6 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 font-medium text-slate-900">{user.email}</td>
                <td className="px-6 py-4">{user.full_name || '-'}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-1 flex-wrap">
                    {user.roles.map(role => (
                      <span key={role} className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        role === 'admin' ? 'bg-purple-100 text-purple-700' :
                        role === 'editor' ? 'bg-blue-100 text-blue-700' :
                        role === 'reviewer' ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-700'
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
                  {user.is_verified ? (
                    <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">Verified</span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-600/20">Unverified</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <button 
                    onClick={() => onEdit(user)}
                    className="text-blue-600 hover:text-blue-800 font-medium text-xs hover:underline"
                  >
                    Edit Role
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-3">
        <div className="text-xs text-slate-500">
          Showing <span className="font-medium">{Math.min((page - 1) * perPage + 1, total)}</span> to <span className="font-medium">{Math.min(page * perPage, total)}</span> of <span className="font-medium">{total}</span> results
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="rounded border border-slate-300 px-3 py-1 text-xs font-medium disabled:opacity-50 hover:bg-slate-50"
          >
            Previous
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="rounded border border-slate-300 px-3 py-1 text-xs font-medium disabled:opacity-50 hover:bg-slate-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
