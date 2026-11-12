from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

from ..services.auth_service import decode_access_token, get_user_by_id


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract raw JWT token from Authorization header value."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Dependency that returns authenticated user if a valid Bearer token is provided,
    or None if unauthenticated. Allows public exploration without requiring login.
    """
    token = extract_bearer_token(authorization)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    return get_user_by_id(payload["sub"])


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Dependency requiring valid authentication. Raises HTTP 401 if token is missing or invalid."""
    user = get_current_user_optional(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Invalid or expired Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
