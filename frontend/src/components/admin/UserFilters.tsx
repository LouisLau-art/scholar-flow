'use client'

import { Search } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface UserFiltersProps {
  search: string;
  role: string;
  onSearchChange: (value: string) => void;
  onRoleChange: (value: string) => void;
}

export function UserFilters({ search, role, onSearchChange, onRoleChange }: UserFiltersProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
      <div className="relative max-w-sm w-full">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <Search className="h-4 w-4 text-slate-400" />
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="block w-full rounded-md border-0 py-1.5 pl-10 text-slate-900 ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
          placeholder="Search by name or email..."
        />
      </div>
      
      <div className="w-full sm:w-auto">
        <Select value={role || '__all'} onValueChange={(value) => onRoleChange(value === '__all' ? '' : value)}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all">All Roles</SelectItem>
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
    </div>
  );
}
