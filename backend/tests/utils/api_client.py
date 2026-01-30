from typing import Dict, Optional

API_PREFIX = "/api/v1"


def auth_headers(token: Optional[str] = None) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
