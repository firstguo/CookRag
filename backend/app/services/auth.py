from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app import setup_logger

# Create module-level logger
logger = setup_logger(__name__)

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
            result = bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
            logger.debug(f"Password verification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Password verification failed with error: {str(e)}")
            return False
    
    def create_token(self, user_id: str) -> str:
        """Create a JWT token for a user."""
        logger.debug(f"Creating JWT token for user: {user_id}")
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
        logger.debug(f"JWT token created successfully for user: {user_id}")
        return token
    
    def verify_token(self, request_or_credentials: Request | HTTPAuthorizationCredentials = None) -> str:
        """Verify JWT token and return user_id."""
        token = None
        
        # Handle both Request object and HTTPAuthorizationCredentials
        if isinstance(request_or_credentials, Request):
            # Extract token from Authorization header
            auth_header = request_or_credentials.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning("Missing or invalid authorization header")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header",
                )
            token = auth_header.split(" ", 1)[1]
        elif isinstance(request_or_credentials, HTTPAuthorizationCredentials):
            token = request_or_credentials.credentials
        else:
            logger.warning("Invalid authentication method")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication method",
            )
        
        try:
            payload = jwt.decode(
                token,
                self._settings.JWT_SECRET,
                algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            if not user_id:
                logger.warning("Invalid token payload - missing user_id")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            logger.debug(f"Token verified successfully for user: {user_id}")
            return user_id
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
