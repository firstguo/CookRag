from fastapi import APIRouter, Depends, HTTPException, Request

from app import setup_logger
from app.models.schemas import RecipeOut
from app.services.auth import AuthService
from app.services.like_service import LikeService
from app.services.mongo_client import MongoDBClient

# Create module-level logger using centralized setup
logger = setup_logger(__name__)


router = APIRouter()


@router.get("/api/recipes/{recipe_id}", response_model=RecipeOut)
async def get_recipe(recipe_id: str, request: Request) -> RecipeOut:
    logger.info(f"Fetching recipe {recipe_id}")
    
    mongo: MongoDBClient = request.app.state.mongo
    
    recipe = mongo.recipe_get(recipe_id)
    if not recipe:
        logger.warning(f"Recipe {recipe_id} not found")
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Try to get user from auth header (optional)
    user_id = None
    try:
        auth_service: AuthService = request.app.state.auth_service
        user_id = auth_service.verify_token(request)
        logger.debug(f"Authenticated user {user_id} accessing recipe {recipe_id}")
    except Exception:
        pass  # User not authenticated, that's OK
    
    # Get like status
    like_count = recipe.get("like_count", 0)
    liked_by_me = False
    
    if user_id:
        like_service: LikeService = request.app.state.like_service
        liked_by_me, like_count = like_service.get_like_status(user_id, recipe_id)
    
    logger.info(f"Successfully retrieved recipe {recipe_id}")
    return RecipeOut(
        id=recipe.get("recipe_id"),
        title_zh=recipe.get("title_zh", ""),
        ingredients=recipe.get("ingredients", []),
        tags=recipe.get("tags", []),
        cook_time_minutes=recipe.get("cook_time_minutes"),
        content_zh=recipe.get("content_zh", ""),
        steps=recipe.get("steps", []),
        like_count=like_count,
        liked_by_me=liked_by_me,
    )

