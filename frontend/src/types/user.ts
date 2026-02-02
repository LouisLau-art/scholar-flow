// T020: Create TypeScript types for user management

export type UserRole = 'author' | 'editor' | 'reviewer' | 'admin';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  roles: UserRole[];
  created_at: string;
  is_verified: boolean;
  
  // Feature 018 Additions
  title?: string | null;
  affiliation?: string | null;
  orcid_id?: string | null;
  google_scholar_url?: string | null;
  avatar_url?: string | null;
  research_interests?: string[];
}

// Alias for single user response
export type UserResponse = User;

export interface Pagination {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface UserListResponse {
  data: User[];
  pagination: Pagination;
}

export interface CreateUserRequest {
  email: string;
  full_name: string;
  role: UserRole;
}

export interface UpdateRoleRequest {
  new_role: UserRole;
  reason: string;
}

export interface InviteReviewerRequest {
  email: string;
  full_name: string;
  manuscript_id?: string;
}

export interface RoleChangeLog {
  id: string;
  user_id: string;
  changed_by: string;
  old_role: string;
  new_role: string;
  reason: string;
  created_at: string;
}
