from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.services.auth import AuthService
from app.services.mongo_client import MongoDBClient


router = APIRouter()


@router.post("/api/auth/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    auth_service: AuthService = request.app.state.auth_service
    mongo: MongoDBClient = request.app.state.mongo
    
    # Hash password
    password_hash = auth_service.hash_password(payload.password)
    
    try:
        user = mongo.user_create(
            nickname=payload.nickname,
            password_hash=password_hash,
        )
        return RegisterResponse(user=UserResponse(**user))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request) -> AuthResponse:
    auth_service: AuthService = request.app.state.auth_service
    mongo: MongoDBClient = request.app.state.mongo
    
    # Find user by nickname
    user = mongo.user_get_by_nickname(payload.nickname)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not auth_service.verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = auth_service.create_token(user["user_id"])
    
    return AuthResponse(
        token=token,
        user=UserResponse(id=user["user_id"], nickname=user["nickname"]),
    )
