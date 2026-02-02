from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.lib.api_client import supabase_admin, create_user_supabase_client
from app.schemas.user import UserProfileUpdate

class UserService:
    def update_profile(self, user_id: UUID, update_data: UserProfileUpdate, access_token: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Update user profile using User Client (enforcing RLS).
        Handles upsert if profile doesn't exist.
        """
        user_client = create_user_supabase_client(access_token)
        
        # Convert Pydantic model to dict, excluding None
        data = update_data.model_dump(exclude_unset=True)
        
        # Ensure URLs are strings
        if 'google_scholar_url' in data and data['google_scholar_url']:
            data['google_scholar_url'] = str(data['google_scholar_url'])
        if 'avatar_url' in data and data['avatar_url']:
            data['avatar_url'] = str(data['avatar_url'])
            
        data['updated_at'] = datetime.now(timezone.utc).isoformat()

        try:
            # Try Update
            resp = user_client.table("user_profiles").update(data).eq("id", str(user_id)).execute()
            rows = getattr(resp, "data", None) or []
            
            if len(rows) == 0:
                # If update failed (no rows), try Insert
                if not email:
                    raise ValueError("Email required for creating new profile")
                
                insert_data = data.copy()
                insert_data['id'] = str(user_id)
                insert_data['email'] = email
                # Default roles if creating new? DB defaults to ['author']
                
                resp = user_client.table("user_profiles").insert(insert_data).execute()
                rows = getattr(resp, "data", None) or [insert_data]
            
            return rows[0]
        except Exception as e:
            print(f"Error updating profile: {e}")
            raise e

    def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Change password using Admin Client.
        """
        try:
            supabase_admin.auth.admin.update_user_by_id(
                str(user_id),
                {"password": new_password}
            )
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            raise e