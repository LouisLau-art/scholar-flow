import os
import secrets
import string
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

def _is_production_env() -> bool:
    value = (
        os.environ.get("GO_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or ""
    )
    return str(value).strip().lower() in {"prod", "production"}

ALLOWED_USER_ROLES = {
    "author",
    "reviewer",
    "owner",
    "managing_editor",
    "assistant_editor",
    "production_editor",
    "editor_in_chief",
    "admin",
}

class UserManagementService:
    """
    Service for handling user management operations including:
    - User creation (admin)
    - Role management
    - Audit logging
    """

    def __init__(self):
        # T014: Implement Supabase client initialization with service role key
        # Service role key is required for admin operations (bypass RLS, manage auth users)
        url: str = os.environ.get("SUPABASE_URL", "")
        service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        
        if not url or not service_key:
            # Fallback or raise error? For now, we print a warning, but this is critical.
            print("WARNING: SUPABASE_SERVICE_ROLE_KEY not set. Admin operations will fail.")
        
        self.admin_client: Client = create_client(url, service_key)

    @staticmethod
    def _generate_temporary_password(length: int = 16) -> str:
        """
        生成高熵临时密码（避免固定弱口令）。
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # --- T015: Implement audit logging helper functions ---

    def log_role_change(self, user_id: UUID, changed_by: UUID, old_role: str, new_role: str, reason: str):
        """
        T015: Log role changes to the database.
        """
        try:
            data = {
                "user_id": str(user_id),
                "changed_by": str(changed_by),
                "old_role": old_role,
                "new_role": new_role,
                "reason": reason,
                "created_at": datetime.utcnow().isoformat()
            }
            self.admin_client.table("role_change_logs").insert(data).execute()
        except Exception as e:
            print(f"Failed to log role change: {e}")
            # Consider if we should raise this or just log error. 
            # Ideally audit logs are critical, so failure might need attention.

    def log_account_creation(self, created_user_id: UUID, created_by: UUID, initial_role: str):
        """
        T015: Log internal account creation events.
        """
        try:
            data = {
                "created_user_id": str(created_user_id),
                "created_by": str(created_by),
                "initial_role": initial_role,
                "created_at": datetime.utcnow().isoformat()
            }
            self.admin_client.table("account_creation_logs").insert(data).execute()
        except Exception as e:
            print(f"Failed to log account creation: {e}")

    def log_email_notification(self, recipient_email: str, notification_type: str, status: str, error_message: Optional[str] = None):
        """
        T015: Log email notification attempts.
        """
        try:
            data = {
                "recipient_email": recipient_email,
                "notification_type": notification_type,
                "status": status,
                "error_message": error_message,
                "sent_at": datetime.utcnow().isoformat()
            }
            self.admin_client.table("email_notification_logs").insert(data).execute()
        except Exception as e:
            print(f"Failed to log email notification: {e}")

    # --- T033, T034: Implement search, filter and pagination logic ---

    def get_users(self, page: int = 1, per_page: int = 10, search: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
        """
        T033, T034: Fetch users from user_profiles with pagination and filters.
        """
        try:
            query = self.admin_client.table("user_profiles").select("*", count="exact")
            
            # Filtering by role
            if role:
                # roles is a text array, we use overlap or contains
                query = query.contains("roles", [role])
            
            # Searching by email or full_name
            if search:
                query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
            
            # Pagination
            offset = (page - 1) * per_page
            query = query.range(offset, offset + per_page - 1).order("created_at", desc=True)
            
            response = query.execute()
            
            total = response.count
            data = response.data
            
            # Map to response format
            users = []
            for item in data:
                users.append({
                    "id": item["id"],
                    "email": item.get("email"),
                    "full_name": item.get("full_name"),
                    "roles": item.get("roles", []),
                    "created_at": item.get("created_at"),
                    "is_verified": True # In user_profiles, we assume they exist. 
                    # Real verification status is in auth.users.email_confirmed_at.
                })
            
            total_pages = (total + per_page - 1) // per_page if total else 0
            
            return {
                "data": users,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages
                }
            }
        except Exception as e:
            print(f"Failed to fetch users: {e}")
            raise Exception(f"Internal server error while fetching users: {e}")

    # --- T057, T058, T059, T060: Implement role change logic ---

    def update_user_role(
        self,
        target_user_id: UUID,
        new_role: Optional[str],
        reason: str,
        changed_by: UUID,
        new_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        T057: Update user role in user_profiles.
        T058: Record audit log.
        T059: 自己修改自己的角色时，仅允许“追加角色”。
        T060: 自己修改自己的角色时，禁止移除 admin。
        """
        target_id_str = str(target_user_id)
        changed_by_str = str(changed_by)
        is_self_update = target_id_str == changed_by_str

        # Fetch current profile to check existence and old role
        try:
            resp = self.admin_client.table("user_profiles").select("*").eq("id", target_id_str).single().execute()
            if not resp.data:
                raise ValueError("User not found")
            
            user_profile = resp.data
            # 统一角色格式：小写 + 去重 + 保序
            current_roles_raw = user_profile.get("roles", []) or []
            current_roles: List[str] = []
            current_seen: set[str] = set()
            for role in current_roles_raw:
                normalized = str(role or "").strip().lower()
                if not normalized or normalized in current_seen:
                    continue
                if normalized in ALLOWED_USER_ROLES:
                    current_seen.add(normalized)
                    current_roles.append(normalized)
            
            requested = new_roles or ([new_role] if new_role else [])
            updated_roles: List[str] = []
            seen: set[str] = set()
            for role in requested:
                normalized = str(role or "").strip().lower()
                if not normalized or normalized in seen:
                    continue
                if normalized not in ALLOWED_USER_ROLES:
                    raise ValueError(f"Invalid role: {normalized}")
                seen.add(normalized)
                updated_roles.append(normalized)
            if not updated_roles:
                raise ValueError("At least one role is required")

            # 方案2：
            # - 允许管理员给自己“追加角色”
            # - 禁止管理员给自己移除任何已有角色（尤其 admin）
            if is_self_update:
                current_role_set = set(current_roles)
                updated_role_set = set(updated_roles)

                if "admin" in current_role_set and "admin" not in updated_role_set:
                    raise ValueError("Cannot remove your own admin role")

                removed_roles = current_role_set - updated_role_set
                if removed_roles:
                    raise ValueError("You can only add roles to yourself")
            
            # Perform update
            update_resp = self.admin_client.table("user_profiles").update({
                "roles": updated_roles,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", target_id_str).execute()
            
            if not update_resp.data:
                raise Exception("Failed to update user profile")
            
            updated_profile = update_resp.data[0]
            
            # T058: Audit Log
            # We log the primary transition.
            old_role_str = ", ".join(current_roles)
            self.log_role_change(
                user_id=target_user_id,
                changed_by=changed_by,
                old_role=old_role_str,
                new_role=", ".join(updated_roles),
                reason=reason
            )
            
            return {
                "id": updated_profile["id"],
                "email": updated_profile.get("email"),
                "full_name": updated_profile.get("full_name"),
                "roles": updated_profile.get("roles", []),
                "created_at": updated_profile.get("created_at"),
                "is_verified": True
            }

        except Exception as e:
            print(f"Update role failed: {e}")
            if (
                "User not found" in str(e)
                or "Cannot modify" in str(e)
                or "Cannot remove your own admin role" in str(e)
                or "You can only add roles to yourself" in str(e)
            ):
                raise e # Re-raise known errors
            raise Exception(f"Internal error updating role: {e}")

    # --- T061: Implement role history retrieval ---

    def get_role_changes(self, target_user_id: UUID) -> List[Dict[str, Any]]:
        """
        T061: Fetch role change history for a user.
        """
        try:
            response = self.admin_client.table("role_change_logs")\
                .select("*")\
                .eq("user_id", str(target_user_id))\
                .order("created_at", desc=True)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"Failed to fetch role history: {e}")
            return []

    def reset_user_password(
        self,
        *,
        target_user_id: UUID,
        changed_by: UUID,
        temporary_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Admin 重置用户密码。
        - 若未显式传入临时密码，则自动生成强随机密码。
        """
        target_id_str = str(target_user_id)
        # 中文注释:
        # - 开发/UAT 阶段为了提速与可复现，默认使用固定口令；
        # - 生产环境必须使用强随机密码，避免弱口令风险。
        if temporary_password is None:
            pwd = "12345678" if not _is_production_env() else self._generate_temporary_password()
        else:
            pwd = str(temporary_password).strip()
        if len(pwd) < 8:
            raise ValueError("Temporary password must be at least 8 characters")

        profile_email: Optional[str] = None
        try:
            profile_resp = (
                self.admin_client.table("user_profiles")
                .select("id,email")
                .eq("id", target_id_str)
                .maybe_single()
                .execute()
            )
            profile = getattr(profile_resp, "data", None) or {}
            profile_email = profile.get("email")
        except Exception:
            # user_profiles 读取失败不阻塞密码重置主流程
            profile_email = None

        try:
            # 兼容现有登录流程：直接设置临时密码并打上 metadata 标记。
            # 前端可据此提示用户尽快到设置页修改密码。
            self.admin_client.auth.admin.update_user_by_id(
                target_id_str,
                {
                    "password": pwd,
                    "user_metadata": {"must_change_password": True},
                },
            )
        except Exception as e:
            msg = str(e)
            if "not found" in msg.lower() or "user not found" in msg.lower():
                raise ValueError("User not found")
            raise Exception(f"Failed to reset password: {msg}") from e

        # 审计：复用邮件日志表记录一次密码重置行为（不发送真实邮件）。
        try:
            self.log_email_notification(
                recipient_email=profile_email or f"user:{target_id_str}",
                notification_type="admin_password_reset",
                status="pending_retry",
                error_message=f"Password reset by admin {changed_by}; delivery not implemented in this flow.",
            )
        except Exception:
            pass

        return {
            "id": target_id_str,
            "email": profile_email,
            "temporary_password": pwd,
            "must_change_password": True,
        }

    # --- T083, T084, T085, T086: Implement user creation logic ---

    def create_internal_user(self, email: str, full_name: str, role: str, created_by: UUID) -> Dict[str, Any]:
        """
        T083: Create user via Supabase Admin API.
        T084: Check uniqueness.
        T085: Audit log.
        T086: Send notification.
        """
        try:
            # 1. Check if user exists (by email) in public.user_profiles or auth.users
            # Checking auth.users via admin API
            try:
                # We can't search by email easily with admin client list_users unless we iterate.
                # But we can try to create and catch error, or check user_profiles first.
                existing = self.admin_client.table("user_profiles").select("id").eq("email", email).maybe_single().execute()
                if existing.data:
                    raise ValueError("User with this email already exists")
            except Exception as e:
                # If checking fails, proceed to create (it will fail if duplicate)
                if "User with this email already exists" in str(e):
                    raise e
            
            # 2. Create user in Supabase Auth
            # We generate a random password or rely on invite magic link?
            # Spec US3: "Direct Invite... sends account notification & initial login credentials".
            # Usually we set a temp password or use inviteUserByEmail.
            # Supabase Python SDK: auth.admin.create_user or invite_user_by_email.
            # invite_user_by_email sends the built-in Supabase invite.
            # But the requirement says "trigger Feature 011 email system".
            # So we might want `create_user` with `email_confirm=True` and a generated password, 
            # then send our own email.
            
            # 中文注释: 同 reset password，开发/UAT 默认固定口令；生产使用强随机。
            temp_password = "12345678" if not _is_production_env() else self._generate_temporary_password(16)
            
            # Note: auth.admin is accessed via self.admin_client.auth.admin
            user_response = self.admin_client.auth.admin.create_user({
                "email": email,
                "password": temp_password,
                "email_confirm": True, # Auto-confirm
                "user_metadata": {"full_name": full_name}
            })
            
            new_user = user_response.user
            if not new_user:
                raise Exception("Failed to create user in Auth")
            
            user_id = new_user.id
            
            # 3. Create/Update user_profiles with role
            # Note: T083 explicitly says "role forced to Editor" in spec input, 
            # but T012 Request model allows role selection. 
            # We'll use the passed role.
            
            profile_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": [role],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.admin_client.table("user_profiles").upsert(profile_data).execute()
            
            # 4. Audit Log
            self.log_account_creation(
                created_user_id=UUID(user_id),
                created_by=created_by,
                initial_role=role
            )
            
            # 5. Send Notification (T086)
            print(f"[UserManagement] internal user created: email={email} role={role}")

            self.log_email_notification(
                recipient_email=email,
                notification_type="account_created",
                # 当前链路仅记录创建事件，未实际发送账号邮件，不应标记 sent。
                status="pending_retry",
                error_message="Account created; delivery not implemented in this flow.",
            )
            
            return {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": [role],
                "created_at": datetime.utcnow().isoformat(),
                "is_verified": True
            }

        except Exception as e:
            print(f"Create user failed: {e}")
            if "already exists" in str(e) or "already registered" in str(e):
                raise ValueError("User with this email already exists")
            raise Exception(f"Internal error creating user: {e}")

    # --- T106, T108, T109: Implement reviewer invitation logic ---

    def invite_reviewer(self, email: str, full_name: str, invited_by: UUID) -> Dict[str, Any]:
        """
        T106: Invite reviewer via Magic Link.
        """
        try:
            # 1. Check existence
            try:
                existing = self.admin_client.table("user_profiles").select("id").eq("email", email).maybe_single().execute()
                if existing.data:
                    raise ValueError("User with this email already exists")
            except Exception as e:
                if "User with this email already exists" in str(e):
                    raise e

            # 2. Generate Invite Link
            # We use generate_link with type="invite" (or "magiclink" if we want to bypass password setup)
            # "invite" sends a link to set password. "magiclink" logs them in.
            # Let's use "magiclink" for smoother onboarding.
            
            # Note: generate_link creates the user if not exists? No, user must exist usually.
            # Wait, `invite_user_by_email` creates user. `generate_link` generates link for existing user.
            # So we must create user first?
            # `admin.generate_link` documentation says: "Generates a link... for a user."
            # So user must exist.
            
            # Step 2a: Create user (shadow account)
            user_id = None
            try:
                temp_password = "12345678" if not _is_production_env() else self._generate_temporary_password(16)
                
                user_response = self.admin_client.auth.admin.create_user({
                    "email": email,
                    "password": temp_password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name}
                })

                if not getattr(user_response, "user", None):
                    # 中文注释: create_user 没抛异常但返回无 user，视为失败（避免误判为“已存在用户”）。
                    raise Exception("Failed to create shadow user")

                user_id = user_response.user.id
            except Exception as create_err:
                # Only treat as "already exists" when the error indicates duplication.
                msg = str(create_err).lower()
                if "already exists" not in msg and "already registered" not in msg:
                    raise

            if not user_id:
                # Fallback 2: Use Auth Admin API to list users and find by email
                # This is the most reliable way to get the ID of an existing user
                try:
                    # Supabase-py list_users() returns a list of users
                    auth_users_res = self.admin_client.auth.admin.list_users()
                    # auth_users_res is a list or contains a users attribute depending on version
                    users_list = getattr(auth_users_res, "users", auth_users_res)
                    if not isinstance(users_list, list):
                        # Some versions return an object with a users list
                        users_list = auth_users_res
                    
                    for u in users_list:
                        if u.email.lower() == email.lower():
                            user_id = u.id
                            break
                except Exception as list_err:
                    print(f"Failed to list users for ID retrieval: {list_err}")

            if not user_id:
                 # CRITICAL: If we still don't have user_id, we cannot return a valid UserResponse.
                 # This happens if the user exists in Auth but we can't find them in the list.
                 raise Exception(f"User '{email}' already exists but ID retrieval failed. Please check Auth dashboard.")

            # Step 2b: Generate link (works for existing users too)
            link_res = self.admin_client.auth.admin.generate_link({
                "type": "magiclink",
                "email": email
            })
            props = getattr(link_res, "properties", None)
            if isinstance(props, dict):
                magic_link = props.get("action_link")
            else:
                magic_link = getattr(props, "action_link", None)
            
            # 3. Create/Update user_profiles
            if user_id:
                # Also update Auth metadata to ensure consistency
                try:
                    self.admin_client.auth.admin.update_user_by_id(
                        user_id, 
                        {"user_metadata": {"full_name": full_name}}
                    )
                except Exception as meta_err:
                    print(f"Failed to update auth metadata: {meta_err}")

                profile_data = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "roles": ["reviewer"], # Default to reviewer
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                self.admin_client.table("user_profiles").upsert(profile_data).execute()
            
                # 4. Audit Log
                self.log_account_creation(
                    created_user_id=UUID(user_id),
                    created_by=invited_by,
                    initial_role="reviewer"
                )
            
            # 5. Send Notification (Email with Magic Link)
            print(f"[UserManagement] reviewer invite link generated for {email}")

            try:
                self.log_email_notification(
                    recipient_email=email,
                    notification_type="reviewer_invite",
                    # 当前链路仅生成链接且不写日志明文，不应标记 sent。
                    status="pending_retry",
                    error_message="Magic link generated; delivery not implemented in this flow.",
                )
            except Exception as log_err:
                print(f"WARNING: Failed to log email notification: {log_err}")
            
            return {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": ["reviewer"],
                "created_at": datetime.utcnow().isoformat(),
                "is_verified": False # Treated as pending until they click
            }

        except Exception as e:
            print(f"Invite reviewer failed: {e}")
            if "already exists" in str(e):
                raise ValueError("User with this email already exists")
            raise Exception(f"Internal error inviting reviewer: {e}")

    
    # def create_user(self, email: str, password: str, data: Dict[str, Any]):
    #     ...
    
    # def update_user_role(self, user_id: UUID, new_role: str):
    #     ...
