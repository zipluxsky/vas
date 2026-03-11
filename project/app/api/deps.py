from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import logging

from app.core.config import settings
from app.services.db_service import DatabaseService
from app.services.email_service import EmailService
from app.integrations.db.mysql import MySQLDatabase
from app.integrations.db.isql import ISQLDatabase

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

def get_db_service(env: str = None) -> DatabaseService:
    """Provide DatabaseService instance. When *env* is given, use that environment's config."""
    if env:
        sybase_cfg = settings.db_config.get('sybase_envs', {}).get(env)
        mysql_cfg = settings.db_config.get('mysql_envs', {}).get(env)
        if sybase_cfg is None:
            logger.warning("No sybase config for env=%s, falling back to default", env)
        if mysql_cfg is None:
            logger.warning("No mysql config for env=%s, falling back to default", env)
        sybase_cfg = sybase_cfg or settings.db_config.get('sybase', {})
        mysql_cfg = mysql_cfg or settings.db_config.get('mysql', {})
    else:
        sybase_cfg = settings.db_config.get('sybase', {})
        mysql_cfg = settings.db_config.get('mysql', {})

    mysql_db = MySQLDatabase(mysql_cfg)
    sybase_db = ISQLDatabase(sybase_cfg)
    return DatabaseService(mysql_db, sybase_db)

def get_email_service() -> EmailService:
    """Dependency to provide EmailService instance"""
    return EmailService(email_config=settings.email_config)

def verify_token(token: str = Depends(oauth2_scheme)):
    """Verify JWT token for standard authentication. Requires SECRET_KEY to be set in environment."""
    if not (getattr(settings, "SECRET_KEY", None) or "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SECRET_KEY is not configured; set SECRET_KEY environment variable",
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
        
    return payload