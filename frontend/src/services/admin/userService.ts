import { authService } from '@/services/auth';
import { 
  UserListResponse, 
  UserResponse, 
  CreateUserRequest, 
  UpdateRoleRequest, 
  InviteReviewerRequest,
  RoleChangeLog
} from '@/types/user';

const API_BASE = '/api/v1/admin/users';

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
