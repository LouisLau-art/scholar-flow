import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { adminUserService } from '@/services/admin/userService';
import { authService } from '@/services/auth';

// Mock authService
vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}));

describe('adminUserService', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getUsers', () => {
    it('fetches users with default parameters', async () => {
      const mockResponse = { data: [], total: 0, page: 1, per_page: 10 };
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await adminUserService.getUsers();

      expect(authService.getAccessToken).toHaveBeenCalled();
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/admin/users?page=1&per_page=10'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('fetches users with search and role', async () => {
      const mockResponse = { data: [], total: 0 };
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await adminUserService.getUsers(2, 20, 'test', 'editor');

      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=2&per_page=20&search=test&role=editor'),
        expect.anything()
      );
    });

    it('throws error when fetch fails', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Unauthorized' }),
      });

      await expect(adminUserService.getUsers()).rejects.toThrow('Unauthorized');
    });
  });

  describe('createUser', () => {
    const mockUser = {
      email: 'new@example.com',
      full_name: 'New User',
      password: 'password123',
      role: 'editor'
    };

    it('creates a user successfully', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ id: '1', ...mockUser }),
      });

      const result = await adminUserService.createUser(mockUser);

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/admin/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(mockUser),
        })
      );
      expect(result).toEqual({ id: '1', ...mockUser });
    });

    it('throws error when creation fails', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Email exists' }),
      });

      await expect(adminUserService.createUser(mockUser)).rejects.toThrow('Email exists');
    });
  });

  describe('updateUserRole', () => {
    it('updates user role successfully', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ id: '1', roles: ['admin'] }),
      });

      await adminUserService.updateUserRole('1', { role: 'admin' });

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/admin/users/1/role',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ role: 'admin' }),
        })
      );
    });

    it('throws error when role update fails', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Update failed' }),
      });

      await expect(adminUserService.updateUserRole('1', { role: 'admin' })).rejects.toThrow('Update failed');
    });
  });

  describe('getRoleChanges', () => {
    it('fetches role changes successfully', async () => {
      const mockLogs = [{ id: 'log1', old_role: 'author', new_role: 'editor' }];
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockLogs,
      });

      const result = await adminUserService.getRoleChanges('1');

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/admin/users/1/role-changes',
        expect.anything()
      );
      expect(result).toEqual(mockLogs);
    });

    it('throws error when fetching logs fails', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Fetch failed' }),
      });

      await expect(adminUserService.getRoleChanges('1')).rejects.toThrow('Fetch failed');
    });
  });

  describe('inviteReviewer', () => {
    const inviteData = {
      email: 'reviewer@example.com',
      full_name: 'Reviewer',
      manuscript_id: 'ms-1'
    };

    it('invites reviewer successfully', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ id: '2', ...inviteData }),
      });

      const result = await adminUserService.inviteReviewer(inviteData);

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/admin/users/invite-reviewer',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(inviteData),
        })
      );
      expect(result).toEqual({ id: '2', ...inviteData });
    });

    it('throws error when invite fails', async () => {
      (globalThis.fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Invite failed' }),
      });

      await expect(adminUserService.inviteReviewer(inviteData)).rejects.toThrow('Invite failed');
    });
  });
});
