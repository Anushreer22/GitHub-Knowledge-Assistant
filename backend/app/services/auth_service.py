import os
import re
import json
import hmac
import base64
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from dataset_pipeline.common import DATA, sid, stream_read, stream_write

USERS_FILE = DATA / "auth" / "users.jsonl"
JWT_SECRET = os.getenv("JWT_SECRET", "github_knowledge_assistant_jwt_secret_phase5_secure_key_2026")
JWT_ALGORITHM = "HS256"


def _b64url_encode(data: bytes) -> str:
    """Base64 URL-safe encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _b64url_decode(data_str: str) -> bytes:
    """Base64 URL-safe decode with padding restoration."""
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += '=' * padding
    return base64.urlsafe_b64decode(data_str.encode('utf-8'))


def hash_password(password: str) -> str:
    """Hash password securely using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify plaintext password against stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_derived = bytes.fromhex(parts[3])

        actual_derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False


def create_access_token(user_id: str, username: str, expires_delta_hours: int = 24) -> str:
    """Create a cryptographically signed RFC 7519 JWT token (HS256)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=expires_delta_hours)

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }

    hdr_b64 = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    pay_b64 = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    message = f"{hdr_b64}.{pay_b64}".encode('utf-8')

    signature = hmac.new(JWT_SECRET.encode('utf-8'), message, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{hdr_b64}.{pay_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token. Returns payload dict if valid, else None."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None

        hdr_b64, pay_b64, sig_b64 = parts
        message = f"{hdr_b64}.{pay_b64}".encode('utf-8')
        expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), message, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(pay_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))

        # Check expiration
        exp = payload.get("exp")
        if exp and exp < datetime.now(timezone.utc).timestamp():
            return None

        return payload
    except Exception:
        return None


def _load_all_users() -> List[Dict[str, Any]]:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        return []
    return list(stream_read(USERS_FILE))


def _save_all_users(users: List[Dict[str, Any]]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = USERS_FILE.with_suffix(".tmp")
    stream_write(tmp_file, users)
    os.replace(tmp_file, USERS_FILE)


def register_user(username: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user with email and secure password hash."""
    clean_u = username.strip()
    clean_e = email.strip().lower()

    if not re.match(r"^[A-Za-z0-9_-]{3,30}$", clean_u):
        raise ValueError("Username must be 3–30 characters long and contain only letters, numbers, hyphens, or underscores.")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_e):
        raise ValueError("Invalid email format.")

    users = _load_all_users()
    for u in users:
        if u["username"].lower() == clean_u.lower():
            raise ValueError(f"Username '{clean_u}' is already taken.")
        if u.get("email", "").lower() == clean_e:
            raise ValueError(f"Email '{clean_e}' is already registered.")

    p_hash = hash_password(password)
    user_id = sid("user", clean_u, clean_e)

    new_user = {
        "user_id": user_id,
        "username": clean_u,
        "email": clean_e,
        "password_hash": p_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "saved_repositories": [],
        "search_history": []
    }
    users.append(new_user)
    _save_all_users(users)

    token = create_access_token(user_id, clean_u)
    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "username": clean_u,
            "email": clean_e,
            "saved_repositories": [],
            "search_history": []
        }
    }


def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate user by username and password. Returns access token and sanitized profile."""
    clean_u = username.strip().lower()
    users = _load_all_users()

    user = next((u for u in users if u["username"].lower() == clean_u or u.get("email", "").lower() == clean_u), None)
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid username or password.")

    token = create_access_token(user["user_id"], user["username"])
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "saved_repositories": user.get("saved_repositories", []),
            "search_history": user.get("search_history", [])
        }
    }


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch sanitized user record by user_id."""
    users = _load_all_users()
    user = next((u for u in users if u["user_id"] == user_id), None)
    if not user:
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "saved_repositories": user.get("saved_repositories", []),
        "search_history": user.get("search_history", [])
    }


def save_repository_for_user(user_id: str, repo_id: str) -> List[str]:
    """Add a repository ID to user's saved list."""
    users = _load_all_users()
    target = next((u for u in users if u["user_id"] == user_id), None)
    if not target:
        raise ValueError("User not found.")

    saved = target.setdefault("saved_repositories", [])
    if repo_id not in saved:
        saved.append(repo_id)
        _save_all_users(users)
    return saved


def remove_saved_repository_for_user(user_id: str, repo_id: str) -> List[str]:
    """Remove a repository ID from user's saved list."""
    users = _load_all_users()
    target = next((u for u in users if u["user_id"] == user_id), None)
    if not target:
        raise ValueError("User not found.")

    saved = target.setdefault("saved_repositories", [])
    if repo_id in saved:
        saved.remove(repo_id)
        _save_all_users(users)
    return saved


def record_search_for_user(user_id: str, query: str, mode: str = "hybrid") -> List[Dict[str, Any]]:
    """Record a search query in user's history (keeps recent 50)."""
    users = _load_all_users()
    target = next((u for u in users if u["user_id"] == user_id), None)
    if not target:
        raise ValueError("User not found.")

    history = target.setdefault("search_history", [])
    history.insert(0, {
        "query": query,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    target["search_history"] = history[:50]
    _save_all_users(users)
    return target["search_history"]
