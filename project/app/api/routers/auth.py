"""Auth router: login (OAuth2 form) and current user / permissions for portal."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import verify_token
from app.core.config import settings
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    permissions_for_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/login/access-token")
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login. Returns access_token for Authorization header."""
    if not (getattr(settings, "SECRET_KEY", None) or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SECRET_KEY is not configured; set SECRET_KEY environment variable",
        )
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = (user.get("role") or "viewer").strip().lower()
    access_token = create_access_token(username=user["username"], role=role)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_current_user_me(payload: dict = Depends(verify_token)):
    """Return current user and permissions for portal menu (reports, settings, admin)."""
    username = payload.get("sub") or ""
    role = (payload.get("role") or "viewer").strip().lower()
    permissions = permissions_for_role(role)
    return {"username": username, "role": role, "permissions": permissions}
