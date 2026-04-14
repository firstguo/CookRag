from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

security = HTTPBearer()


class AuthService:
    def __init__(self, settings: Settings):
        self._settings = settings
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    def create_token(self, user_id: str) -> str:
        """Create a JWT token for a user."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.JWT_EXPIRE_MINUTES
        )
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(
            payload,
            self._settings.JWT_SECRET,
            algorithm="HS256"
        )
        return token
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """Verify JWT token and return user_id."""
        try:
            payload = jwt.decode(
                credentials.credentials,
                self._settings.JWT_SECRET,
                algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
