from fastapi import APIRouter, HTTPException, Request

from app import setup_logger
from app.models.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.services.auth import AuthService
from app.services.mongo_client import MongoDBClient

# Create module-level logger using centralized setup
logger = setup_logger(__name__)


router = APIRouter()


@router.post("/api/auth/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    logger.info(f"Registration attempt for nickname: {payload.nickname}")
    
    auth_service: AuthService = request.app.state.auth_service
    mongo: MongoDBClient = request.app.state.mongo
    
    # Hash password
    password_hash = auth_service.hash_password(payload.password)
    
    try:
        user = mongo.user_create(
            nickname=payload.nickname,
            password_hash=password_hash,
        )
        logger.info(f"User registered successfully: {payload.nickname}")
        return RegisterResponse(user=UserResponse(**user))
    except ValueError as e:
        logger.warning(f"Registration failed for {payload.nickname}: {str(e)}")
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request) -> AuthResponse:
    logger.info(f"Login attempt for nickname: {payload.nickname}")
    
    auth_service: AuthService = request.app.state.auth_service
    mongo: MongoDBClient = request.app.state.mongo
    
    # Find user by nickname
    user = mongo.user_get_by_nickname(payload.nickname)
    if not user:
        logger.warning(f"Login failed - user not found: {payload.nickname}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not auth_service.verify_password(payload.password, user.get("password_hash", "")):
        logger.warning(f"Login failed - invalid password for: {payload.nickname}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = auth_service.create_token(user["user_id"])
    
    logger.info(f"User logged in successfully: {payload.nickname}")
    return AuthResponse(
        token=token,
        user=UserResponse(id=user["user_id"], nickname=user["nickname"]),
    )
