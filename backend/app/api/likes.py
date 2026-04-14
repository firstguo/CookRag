from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import LikeResponse
from app.services.auth import AuthService
from app.services.like_service import LikeService
from app.services.mongo_client import MongoDBClient


router = APIRouter()


@router.post("/api/recipes/{recipe_id}/like", response_model=LikeResponse)
async def like_recipe(recipe_id: str, request: Request) -> LikeResponse:
    # Verify authentication
    auth_service: AuthService = request.app.state.auth_service
    try:
        user_id = auth_service.verify_token(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if recipe exists
    mongo: MongoDBClient = request.app.state.mongo
    recipe = mongo.recipe_get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Like the recipe
    like_service: LikeService = request.app.state.like_service
    liked_by_me, like_count = like_service.like_recipe(user_id, recipe_id)
    
    return LikeResponse(liked_by_me=liked_by_me, like_count=like_count)


@router.delete("/api/recipes/{recipe_id}/like", response_model=LikeResponse)
async def unlike_recipe(recipe_id: str, request: Request) -> LikeResponse:
    # Verify authentication
    auth_service: AuthService = request.app.state.auth_service
    try:
        user_id = auth_service.verify_token(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if recipe exists
    mongo: MongoDBClient = request.app.state.mongo
    recipe = mongo.recipe_get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Unlike the recipe
    like_service: LikeService = request.app.state.like_service
    liked_by_me, like_count = like_service.unlike_recipe(user_id, recipe_id)
    
    return LikeResponse(liked_by_me=liked_by_me, like_count=like_count)
