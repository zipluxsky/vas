"""Authentication service: load users from config, verify password, issue JWT, resolve permissions by role."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import bcrypt
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Role -> menu permissions: reports, settings, admin
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["reports", "settings", "admin"],
    "user": ["reports", "settings"],
    "viewer": ["reports"],
}


def _users_config_path() -> Path:
    """Resolve users config: prefer configs/python_config/users.json, then app/core/users.json."""
    base = settings.BASE_DIR
    external = base.parent / "configs" / "python_config" / "users.json"
    if external.exists():
        return external
    return base / "app" / "core" / "users.json"


def load_users() -> List[Dict[str, Any]]:
    """Load users list from JSON config."""
    path = _users_config_path()
    if not path.exists():
        logger.warning("Users config not found at %s", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("users", [])
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load users config %s: %s", path, e)
        return []


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify plain password against stored bcrypt hash (using bcrypt lib for compatibility)."""
    if not password_hash or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception as e:
        logger.debug("Password verify error: %s", e)
        return False


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Return user dict (username, password_hash, role) if found."""
    users = load_users()
    for u in users:
        if (u.get("username") or "").strip().lower() == (username or "").strip().lower():
            return u
    return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """If credentials are valid, return user dict (with role); else None."""
    user = get_user_by_username(username)
    if not user:
        return None
    phash = user.get("password_hash") or ""
    if not phash or not verify_password(password, phash):
        return None
    return user


def permissions_for_role(role: str) -> List[str]:
    """Return list of permission keys (reports, settings, admin) for the given role."""
    return list(ROLE_PERMISSIONS.get((role or "").strip().lower(), []))


def create_access_token(username: str, role: str) -> str:
    """Create JWT with sub=username, role, and exp."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
