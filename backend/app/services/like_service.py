from __future__ import annotations

from app.services.mongo_client import MongoDBClient


class LikeService:
    def __init__(self, mongo: MongoDBClient):
        self._mongo = mongo
    
    def like_recipe(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Like a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        # Try to add like (idempotent)
        added = self._mongo.like_add(user_id, recipe_id)
        
        if added:
            # Increment like count
            self._mongo.recipe_update_like_count(recipe_id, 1)
        
        # Get updated like count
        like_count = self._mongo.like_count_get(recipe_id)
        
        return True, like_count
    
    def unlike_recipe(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Unlike a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        # Try to remove like (idempotent)
        removed = self._mongo.like_remove(user_id, recipe_id)
        
        if removed:
            # Decrement like count
            self._mongo.recipe_update_like_count(recipe_id, -1)
        
        # Get updated like count
        like_count = self._mongo.like_count_get(recipe_id)
        
        return False, like_count
    
    def get_like_status(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Get like status for a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        liked_by_me = self._mongo.like_check(user_id, recipe_id)
        like_count = self._mongo.like_count_get(recipe_id)
        
        return liked_by_me, like_count
