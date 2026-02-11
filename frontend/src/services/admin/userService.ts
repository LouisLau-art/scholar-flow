import { authService } from '@/services/auth';
import { 
  UserListResponse, 
  UserResponse, 
  CreateUserRequest, 
  UpdateRoleRequest, 
  InviteReviewerRequest,
  RoleChangeLog,
  JournalScopeItem,
  ResetPasswordRequest,
  ResetPasswordResponse,
} from '@/types/user';

const API_BASE = '/api/v1/admin/users';
const JOURNAL_SCOPE_API = '/api/v1/admin/journal-scopes';

async function getAuthHeader() {
  const token = await authService.getAccessToken();
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

export const adminUserService = {
  // T037: Implement getUsers() method
  async getUsers(page = 1, perPage = 10, search = '', role = ''): Promise<UserListResponse> {
    const headers = await getAuthHeader();
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString()
    });
    if (search) params.append('search', search);
    if (role) params.append('role', role);

    const res = await fetch(`${API_BASE}?${params.toString()}`, { headers });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to fetch users');
    }
    return res.json();
  },

  // T088: Implement createInternalEditor() method
  async createUser(data: CreateUserRequest): Promise<UserResponse> {
    const headers = await getAuthHeader();
    const res = await fetch(API_BASE, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to create user');
    }
    return res.json();
  },

  // T063: Implement updateUserRole() method
  async updateUserRole(userId: string, data: UpdateRoleRequest): Promise<UserResponse> {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/${userId}/role`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to update role');
    }
    return res.json();
  },

  async listJournalScopes(params?: { userId?: string; journalId?: string; isActive?: boolean }): Promise<JournalScopeItem[]> {
    const headers = await getAuthHeader();
    const query = new URLSearchParams();
    if (params?.userId) query.set('user_id', params.userId);
    if (params?.journalId) query.set('journal_id', params.journalId);
    if (typeof params?.isActive === 'boolean') query.set('is_active', String(params.isActive));
    const suffix = query.toString() ? `?${query.toString()}` : '';
    const res = await fetch(`${JOURNAL_SCOPE_API}${suffix}`, { headers });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to fetch journal scopes');
    }
    return res.json();
  },

  async resetUserPassword(
    userId: string,
    data: ResetPasswordRequest = {}
  ): Promise<ResetPasswordResponse> {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/${userId}/reset-password`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to reset password');
    }
    return res.json();
  },

  // T064: Implement getRoleChanges() method
  async getRoleChanges(userId: string): Promise<RoleChangeLog[]> {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/${userId}/role-changes`, { headers });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to fetch role changes');
    }
    return res.json();
  },

  // T110: Implement inviteReviewer() method
  async inviteReviewer(data: InviteReviewerRequest): Promise<UserResponse> {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/invite-reviewer`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to invite reviewer');
    }
    return res.json();
  }
};
