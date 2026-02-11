'use client'

import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { adminUserService } from '@/services/admin/userService';
import { authService } from '@/services/auth';
import { UserTable } from '@/components/admin/UserTable';
import { UserFilters } from '@/components/admin/UserFilters';
import { UserRoleDialog } from '@/components/admin/UserRoleDialog';
import { CreateUserDialog } from '@/components/admin/CreateUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { User, UserRole } from '@/types/user';
import { toast } from 'sonner';
import { Loader2, ShieldAlert } from 'lucide-react';
import SiteHeader from '@/components/layout/SiteHeader';
import { Button } from '@/components/ui/button';

export default function UserManagementPage() {
  const router = useRouter();
  // Auth State
  const [verifyingRole, setVerifyingRole] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  // Data State
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  
  // Dialog State
  const [isRoleDialogOpen, setIsRoleDialogOpen] = useState(false);
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  
  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  // 1. Security Check: Verify Admin Role on Mount
  useEffect(() => {
    async function checkAdminAccess() {
      try {
        const session = await authService.getSession();
        if (!session?.user) {
          router.replace('/login');
          return;
        }

        // Fetch user profile to get roles
        const profile = await authService.getUserProfile();
        const roles = profile?.roles || [];
        
        if (!roles.includes('admin')) {
          toast.error('Access Denied: You do not have permission to view this page.');
          router.replace('/dashboard'); // Redirect unauthorized users
        } else {
          setIsAdmin(true);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        router.replace('/dashboard');
      } finally {
        setVerifyingRole(false);
      }
    }
    checkAdminAccess();
  }, [router]);

  // 2. Data Fetching (Only if Admin)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); 
    }, 500);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchUsers = useCallback(async () => {
    if (!isAdmin) return; // Stop fetching if not admin

    setLoading(true);
    try {
      const response = await adminUserService.getUsers(page, 10, debouncedSearch, role);
      setUsers(response.data);
      setTotal(response.pagination.total);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      // Don't toast here if it's a 403, as the initial check should handle it.
      // But for robust UX, we can check status.
      toast.error('Failed to load users.');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, role, isAdmin]);

  useEffect(() => {
    if (isAdmin) {
      fetchUsers();
    }
  }, [fetchUsers, isAdmin]);

  // 3. Actions
  const handleRoleChange = (newRole: string) => {
    setRole(newRole);
    setPage(1);
  };

  const handleEditClick = (user: User) => {
    setSelectedUser(user);
    setIsRoleDialogOpen(true);
  };

  const handleResetPasswordClick = (user: User) => {
    setSelectedUser(user);
    setIsResetDialogOpen(true);
  };

  const handleRoleUpdate = async (userId: string, newRoles: UserRole[], reason: string) => {
    try {
      await adminUserService.updateUserRole(userId, { new_roles: newRoles, reason });
      toast.success('User roles updated successfully');
      fetchUsers(); 
    } catch (error) {
      console.error('Update failed:', error);
      throw error;
    }
  };

  const handleInviteUser = async (email: string, fullName: string, role: UserRole) => {
    try {
      await adminUserService.createUser({ email, full_name: fullName, role });
      toast.success('Invitation sent successfully!');
      fetchUsers(); 
    } catch (error) {
      console.error('Invite failed:', error);
      throw error; 
    }
  };

  const handleResetPassword = async (userId: string) => {
    try {
      await adminUserService.resetUserPassword(userId, { temporary_password: '12345678' });
      toast.success('Password reset to 12345678');
    } catch (error) {
      console.error('Reset password failed:', error);
      throw error;
    }
  };

  let content: ReactNode;

  // 4. Render Loading or Access Denied state
  if (verifyingRole) {
    content = (
      <div className="flex flex-1 w-full items-center justify-center flex-col gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
        <p className="text-slate-500 font-medium">Verifying access privileges...</p>
      </div>
    )
  } else if (!isAdmin) {
    content = (
      <div className="flex flex-1 w-full items-center justify-center flex-col gap-4">
        <ShieldAlert className="h-12 w-12 text-red-500" />
        <h1 className="text-xl font-bold text-slate-900">Access Denied</h1>
        <p className="text-slate-500">Redirecting you to dashboard...</p>
      </div>
    )
  } else {
    // 5. Render Admin Page
    content = (
      <div className="w-full">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
            <p className="mt-1 text-sm text-slate-500">
              Manage user accounts, roles, and permissions.
            </p>
          </div>
          <Button onClick={() => setIsInviteDialogOpen(true)}>
            Invite Member
          </Button>
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
            onResetPassword={handleResetPasswordClick}
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

        <ResetPasswordDialog
          isOpen={isResetDialogOpen}
          onClose={() => setIsResetDialogOpen(false)}
          onConfirm={handleResetPassword}
          user={selectedUser}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-10 sm:px-6 lg:px-8">
        {content}
      </main>
    </div>
  );
}
