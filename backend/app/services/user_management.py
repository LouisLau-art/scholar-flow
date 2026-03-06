import os
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

from app.core.default_password import get_default_bootstrap_password
from app.core.mail import email_service

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


logger = logging.getLogger("scholarflow.user_management")

_EMAIL_TEMPLATE_TABLE = "email_templates"
_EMAIL_TEMPLATE_SCENE = "admin_user_management"
_DEFAULT_EMAIL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "admin_internal_user_welcome": {
        "template_key": "admin_internal_user_welcome",
        "display_name": "内部账号开通通知",
        "scene": _EMAIL_TEMPLATE_SCENE,
        "subject_template": "[{{ journal_title }}] Your account is ready",
        "body_html_template": (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>Your account has been created in <strong>{{ journal_title }}</strong>.</p>"
            "<p>Assigned role: <strong>{{ role_label }}</strong></p>"
            "<p>Sign in here: <a href=\"{{ login_url }}\">{{ login_url }}</a></p>"
            "<p>Default password: <strong>{{ default_password }}</strong></p>"
            "<p>Best regards,<br/>{{ journal_title }} Editorial Office</p>"
        ),
        "body_text_template": (
            "Dear {{ recipient_name }}, your {{ journal_title }} account (role: {{ role_label }}) is ready. "
            "Sign in here: {{ login_url }}. Default password: {{ default_password }}"
        ),
    },
    "admin_password_reset_link": {
        "template_key": "admin_password_reset_link",
        "display_name": "管理员重置密码通知",
        "scene": _EMAIL_TEMPLATE_SCENE,
        "subject_template": "[{{ journal_title }}] Password reset completed",
        "body_html_template": (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>An administrator reset the password for your account in <strong>{{ journal_title }}</strong>.</p>"
            "<p>Sign in here: <a href=\"{{ login_url }}\">{{ login_url }}</a></p>"
            "<p>New password: <strong>{{ default_password }}</strong></p>"
            "<p>If you did not expect this change, please contact support immediately.</p>"
        ),
        "body_text_template": (
            "Your {{ journal_title }} password has been reset. "
            "Sign in here: {{ login_url }}. New password: {{ default_password }}"
        ),
    },
    "admin_reviewer_invite": {
        "template_key": "admin_reviewer_invite",
        "display_name": "审稿人平台邀请",
        "scene": _EMAIL_TEMPLATE_SCENE,
        "subject_template": "[{{ journal_title }}] Reviewer account invitation",
        "body_html_template": (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>You have been invited as a reviewer on <strong>{{ journal_title }}</strong>.</p>"
            "<p>Sign in here: <a href=\"{{ login_url }}\">{{ login_url }}</a></p>"
            "<p>Default password: <strong>{{ default_password }}</strong></p>"
            "<p>After sign-in, you can access reviewer workflows in your dashboard.</p>"
        ),
        "body_text_template": (
            "You are invited as a reviewer on {{ journal_title }}. "
            "Sign in here: {{ login_url }}. Default password: {{ default_password }}"
        ),
    },
}


def _mask_email(email: str | None) -> str:
    value = str(email or "").strip()
    if "@" not in value:
        return "<empty>"
    local, domain = value.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[:1]}***@{domain}"


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
            logger.warning("SUPABASE_SERVICE_ROLE_KEY not set. Admin operations will fail.")
        
        self.admin_client: Client = create_client(url, service_key)

    @staticmethod
    def _get_frontend_base_url() -> str:
        raw = (
            os.environ.get("FRONTEND_BASE_URL")
            or os.environ.get("FRONTEND_ORIGIN")
            or "http://localhost:3000"
        )
        return str(raw).strip().rstrip("/")

    @staticmethod
    def _default_journal_title() -> str:
        return (
            os.environ.get("JOURNAL_TITLE")
            or os.environ.get("SITE_NAME")
            or "ScholarFlow Journal"
        ).strip()

    def _build_login_url(self) -> str:
        return f"{self._get_frontend_base_url()}/login"

    def _load_email_template(self, *, env_key: str, fallback_key: str) -> Dict[str, Any]:
        configured_key = str(os.environ.get(env_key) or "").strip() or fallback_key
        try:
            res = (
                self.admin_client.table(_EMAIL_TEMPLATE_TABLE)
                .select(
                    "template_key,display_name,scene,subject_template,body_html_template,body_text_template,is_active"
                )
                .eq("template_key", configured_key)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
            row = getattr(res, "data", None)
            if row:
                return row
        except Exception as e:
            # 中文注释：模板表缺失或查询失败时回退内置模板，避免主流程中断。
            logger.warning("Failed to load email template '%s': %s", configured_key, e)
        return dict(_DEFAULT_EMAIL_TEMPLATES.get(fallback_key) or {})

    def _send_inline_email(
        self,
        *,
        to_email: str,
        template: Dict[str, Any],
        context: Dict[str, Any],
        idempotency_key: str,
        tags: Optional[List[Dict[str, str]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> tuple[bool, str]:
        if not email_service.is_configured():
            return False, "Email service is not configured"

        subject_template = str(template.get("subject_template") or "").strip()
        body_html_template = str(template.get("body_html_template") or "").strip()
        body_text_template = str(template.get("body_text_template") or "").strip() or None
        template_key = str(template.get("template_key") or "inline_template").strip()

        if not subject_template or not body_html_template:
            return False, f"Email template '{template_key}' is invalid"

        try:
            subject = email_service.render_inline_template(subject_template, context).strip() or "(no subject)"
            html_body = email_service.render_inline_template(body_html_template, context)
            text_body = (
                email_service.render_inline_template(body_text_template, context)
                if body_text_template
                else email_service._build_plain_text_from_html(html_body)
            )
            ok = email_service.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                idempotency_key=idempotency_key,
                tags=tags,
                headers=headers,
            )
            return ok, "" if ok else "Email provider returned failure"
        except Exception as e:
            logger.warning("Failed to send inline email to %s: %s", _mask_email(to_email), e)
            return False, str(e)

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
            logger.warning("Failed to log role change: %s", e)
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
            logger.warning("Failed to log account creation: %s", e)

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
            logger.warning("Failed to log email notification: %s", e)

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
            logger.error("Failed to fetch users: %s", e)
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
            logger.error("Update role failed: %s", e)
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
            logger.warning("Failed to fetch role history: %s", e)
            return []

    def reset_user_password(
        self,
        *,
        target_user_id: UUID,
        changed_by: UUID,
        redirect_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Admin 直接重置用户密码为开发阶段固定口令。
        """
        target_id_str = str(target_user_id)
        profile_email: Optional[str] = None
        profile_name: Optional[str] = None
        try:
            profile_resp = (
                self.admin_client.table("user_profiles")
                .select("id,email,full_name")
                .eq("id", target_id_str)
                .maybe_single()
                .execute()
            )
            profile = getattr(profile_resp, "data", None) or {}
            profile_email = profile.get("email")
            profile_name = profile.get("full_name")
        except Exception:
            # user_profiles 读取失败不阻塞后续处理；若无 email 会在下方显式报错。
            profile_email = None

        if not profile_email:
            raise ValueError("User not found")

        try:
            auth_res = self.admin_client.auth.admin.get_user_by_id(target_id_str)
            auth_user = getattr(auth_res, "user", None)
            auth_metadata = getattr(auth_user, "user_metadata", None) or {}
            if not isinstance(auth_metadata, dict):
                auth_metadata = {}
        except Exception as e:
            logger.warning("Failed to fetch auth metadata before password reset: %s", e)
            auth_metadata = {}

        try:
            self.admin_client.auth.admin.update_user_by_id(
                target_id_str,
                {
                    "password": get_default_bootstrap_password(),
                    "user_metadata": {
                        **auth_metadata,
                        "must_change_password": False,
                    },
                },
            )
        except Exception as e:
            msg = str(e)
            if "not found" in msg.lower() or "user not found" in msg.lower():
                raise ValueError("User not found")
            raise Exception(f"Failed to reset password: {msg}") from e

        template = self._load_email_template(
            env_key="ADMIN_PASSWORD_RESET_EMAIL_TEMPLATE_KEY",
            fallback_key="admin_password_reset_link",
        )
        login_url = self._build_login_url()
        default_password = get_default_bootstrap_password()
        context = {
            "recipient_name": str(profile_name or "").strip() or str(profile_email).split("@")[0],
            "journal_title": self._default_journal_title(),
            "action_link": login_url,
            "login_url": login_url,
            "default_password": default_password,
            "user_email": profile_email,
        }
        timestamp = int(datetime.utcnow().timestamp())
        sent, send_error = self._send_inline_email(
            to_email=profile_email,
            template=template,
            context=context,
            idempotency_key=f"admin-reset-password:{target_id_str}:{timestamp}",
            tags=[
                {"name": "scene", "value": _EMAIL_TEMPLATE_SCENE},
                {"name": "event", "value": "admin_password_reset"},
            ],
            headers={
                "X-SF-Event": "admin_password_reset",
                "X-SF-User-ID": target_id_str,
            },
        )
        if not sent:
            self.log_email_notification(
                recipient_email=profile_email,
                notification_type="admin_password_reset",
                status="pending_retry",
                error_message=send_error or "Failed to send reset password email",
            )
        else:
            self.log_email_notification(
                recipient_email=profile_email,
                notification_type="admin_password_reset",
                status="sent",
            )

        return {
            "id": target_id_str,
            "email": profile_email,
            "must_change_password": False,
            "reset_link_sent": False,
            "delivery_status": "pending_retry" if not sent else "sent",
            "temporary_password": default_password,
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
            try:
                existing = self.admin_client.table("user_profiles").select("id").eq("email", email).maybe_single().execute()
                if existing.data:
                    raise ValueError("User with this email already exists")
            except Exception as e:
                if "User with this email already exists" in str(e):
                    raise e

            user_response = self.admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": get_default_bootstrap_password(),
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name},
                }
            )
            
            new_user = user_response.user
            if not new_user:
                raise Exception("Failed to create user in Auth")
            
            user_id = new_user.id
            profile_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": [role],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.admin_client.table("user_profiles").upsert(profile_data).execute()
            
            self.log_account_creation(
                created_user_id=UUID(user_id),
                created_by=created_by,
                initial_role=role
            )

            logger.info(
                "[UserManagement] internal user created: email=%s role=%s",
                _mask_email(email),
                role,
            )
            template = self._load_email_template(
                env_key="ADMIN_INTERNAL_USER_EMAIL_TEMPLATE_KEY",
                fallback_key="admin_internal_user_welcome",
            )
            context = {
                "recipient_name": full_name,
                "journal_title": self._default_journal_title(),
                "action_link": self._build_login_url(),
                "login_url": self._build_login_url(),
                "default_password": get_default_bootstrap_password(),
                "role_label": role.replace("_", " ").title(),
                "user_email": email,
            }
            timestamp = int(datetime.utcnow().timestamp())
            sent, send_error = self._send_inline_email(
                to_email=email,
                template=template,
                context=context,
                idempotency_key=f"admin-create-user:{user_id}:{timestamp}",
                tags=[
                    {"name": "scene", "value": _EMAIL_TEMPLATE_SCENE},
                    {"name": "event", "value": "admin_internal_user_created"},
                ],
                headers={
                    "X-SF-Event": "admin_internal_user_created",
                    "X-SF-User-ID": str(user_id),
                    "X-SF-Role": role,
                },
            )
            if not sent:
                self.log_email_notification(
                    recipient_email=email,
                    notification_type="account_created",
                    status="pending_retry",
                    error_message=send_error or "Failed to send account creation email",
                )
                raise Exception("Internal user created, but welcome email delivery failed")

            self.log_email_notification(
                recipient_email=email,
                notification_type="account_created",
                status="sent",
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
            logger.error("Create user failed: %s", e)
            if "already exists" in str(e) or "already registered" in str(e):
                raise ValueError("User with this email already exists")
            raise Exception(f"Internal error creating user: {e}")

    # --- T106, T108, T109: Implement reviewer invitation logic ---

    def invite_reviewer(self, email: str, full_name: str, invited_by: UUID) -> Dict[str, Any]:
        """
        T106: Invite reviewer and deliver onboarding email.
        """
        try:
            try:
                existing = self.admin_client.table("user_profiles").select("id").eq("email", email).maybe_single().execute()
                if existing.data:
                    raise ValueError("User with this email already exists")
            except Exception as e:
                if "User with this email already exists" in str(e):
                    raise e

            user_response = self.admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": get_default_bootstrap_password(),
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name},
                }
            )
            if not getattr(user_response, "user", None):
                raise Exception("Failed to create reviewer user")
            user_id = str(user_response.user.id)
            
            profile_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": ["reviewer"],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            self.admin_client.table("user_profiles").upsert(profile_data).execute()
            self.log_account_creation(
                created_user_id=UUID(user_id),
                created_by=invited_by,
                initial_role="reviewer",
            )
            
            logger.info("[UserManagement] reviewer invite link generated for %s", _mask_email(email))
            template = self._load_email_template(
                env_key="ADMIN_REVIEWER_INVITE_EMAIL_TEMPLATE_KEY",
                fallback_key="admin_reviewer_invite",
            )
            context = {
                "recipient_name": full_name,
                "journal_title": self._default_journal_title(),
                "action_link": self._build_login_url(),
                "login_url": self._build_login_url(),
                "default_password": get_default_bootstrap_password(),
                "reviewer_email": email,
            }
            timestamp = int(datetime.utcnow().timestamp())
            sent, send_error = self._send_inline_email(
                to_email=email,
                template=template,
                context=context,
                idempotency_key=f"admin-invite-reviewer:{user_id}:{timestamp}",
                tags=[
                    {"name": "scene", "value": _EMAIL_TEMPLATE_SCENE},
                    {"name": "event", "value": "admin_reviewer_invite"},
                ],
                headers={
                    "X-SF-Event": "admin_reviewer_invite",
                    "X-SF-User-ID": user_id,
                },
            )
            if not sent:
                self.log_email_notification(
                    recipient_email=email,
                    notification_type="reviewer_invite",
                    status="pending_retry",
                    error_message=send_error or "Failed to send reviewer invite email",
                )
                raise Exception("Reviewer created, but invitation email delivery failed")
            self.log_email_notification(
                recipient_email=email,
                notification_type="reviewer_invite",
                status="sent",
            )
            
            return {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "roles": ["reviewer"],
                "created_at": datetime.utcnow().isoformat(),
                "is_verified": False,
            }

        except Exception as e:
            logger.error("Invite reviewer failed: %s", e)
            if "already exists" in str(e):
                raise ValueError("User with this email already exists")
            raise Exception(f"Internal error inviting reviewer: {e}")

    
    # def create_user(self, email: str, password: str, data: Dict[str, Any]):
    #     ...
    
    # def update_user_role(self, user_id: UUID, new_role: str):
    #     ...
