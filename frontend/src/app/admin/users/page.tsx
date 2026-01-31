'use client'

import { useState, useEffect } from 'react';
import { adminUserService } from '@/services/admin/userService';
import { UserTable } from '@/components/admin/UserTable';
import { UserFilters } from '@/components/admin/UserFilters';
import { UserRoleDialog } from '@/components/admin/UserRoleDialog';
import { CreateUserDialog } from '@/components/admin/CreateUserDialog';
import { User, UserRole } from '@/types/user';
import { toast } from 'sonner';

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  
  // Dialog State
  const [isRoleDialogOpen, setIsRoleDialogOpen] = useState(false);
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  
  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // Reset page on search change
    }, 500);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    fetchUsers();
  }, [page, debouncedSearch, role]);

  async function fetchUsers() {
    setLoading(true);
    try {
      const response = await adminUserService.getUsers(page, 10, debouncedSearch, role);
      setUsers(response.data);
      setTotal(response.pagination.total);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      toast.error('Failed to load users. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const handleRoleChange = (newRole: string) => {
    setRole(newRole);
    setPage(1);
  };

  const handleEditClick = (user: User) => {
    setSelectedUser(user);
    setIsRoleDialogOpen(true);
  };

  const handleRoleUpdate = async (userId: string, newRole: UserRole, reason: string) => {
    try {
      await adminUserService.updateUserRole(userId, { new_role: newRole, reason });
      toast.success('User role updated successfully');
      fetchUsers(); // Refresh list
    } catch (error) {
      console.error('Update failed:', error);
      throw error; // Let dialog handle the error display
    }
  };

  const handleInviteUser = async (email: string, fullName: string, role: UserRole) => {
    try {
      await adminUserService.createUser({ email, full_name: fullName, role });
      toast.success('Invitation sent successfully!');
      fetchUsers(); // Refresh list
    } catch (error) {
      console.error('Invite failed:', error);
      throw error;
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage user accounts, roles, and permissions.
          </p>
        </div>
        <button 
          onClick={() => setIsInviteDialogOpen(true)}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          Invite Member
        </button>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
        <UserFilters 
          search={search} 
          role={role} 
          onSearchChange={setSearch} 
          onRoleChange={handleRoleChange} 
        />
        
        <UserTable 
          users={users} 
          isLoading={loading} 
          page={page} 
          perPage={10} 
          total={total} 
          onPageChange={setPage} 
          onEdit={handleEditClick}
        />
      </div>

      <UserRoleDialog 
        isOpen={isRoleDialogOpen} 
        onClose={() => setIsRoleDialogOpen(false)} 
        onConfirm={handleRoleUpdate}
        user={selectedUser}
      />

      <CreateUserDialog 
        isOpen={isInviteDialogOpen} 
        onClose={() => setIsInviteDialogOpen(false)} 
        onConfirm={handleInviteUser}
      />
    </div>
  );
}
