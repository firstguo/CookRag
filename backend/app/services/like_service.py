from __future__ import annotations

import logging

from app import setup_logger
from app.services.mongo_client import MongoDBClient

# Create module-level logger
logger = setup_logger(__name__)


class LikeService:
    def __init__(self, mongo: MongoDBClient):
        self._mongo = mongo
    
    def like_recipe(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Like a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        logger.info(f"User {user_id} attempting to like recipe {recipe_id}")
        
        # Try to add like (idempotent)
        added = self._mongo.like_add(user_id, recipe_id)
        
        if added:
            logger.info(f"User {user_id} successfully liked recipe {recipe_id}")
            # Increment like count
            self._mongo.recipe_update_like_count(recipe_id, 1)
        else:
            logger.info(f"User {user_id} already liked recipe {recipe_id}, no change")
        
        # Get updated like count and check actual status
        like_count = self._mongo.like_count_get(recipe_id)
        liked_by_me = self._mongo.like_check(user_id, recipe_id)
        
        logger.info(f"Recipe {recipe_id} like status: liked_by_me={liked_by_me}, like_count={like_count}")
        return liked_by_me, like_count
    
    def unlike_recipe(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Unlike a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        logger.info(f"User {user_id} attempting to unlike recipe {recipe_id}")
        
        # Try to remove like (idempotent)
        removed = self._mongo.like_remove(user_id, recipe_id)
        
        if removed:
            logger.info(f"User {user_id} successfully unliked recipe {recipe_id}")
            # Decrement like count
            self._mongo.recipe_update_like_count(recipe_id, -1)
        else:
            logger.info(f"User {user_id} had not liked recipe {recipe_id}, no change")
        
        # Get updated like count and check actual status
        like_count = self._mongo.like_count_get(recipe_id)
        liked_by_me = self._mongo.like_check(user_id, recipe_id)
        
        logger.info(f"Recipe {recipe_id} like status: liked_by_me={liked_by_me}, like_count={like_count}")
        return liked_by_me, like_count
    
    def get_like_status(self, user_id: str, recipe_id: str) -> tuple[bool, int]:
        """
        Get like status for a recipe.
        
        Returns:
            (liked_by_me, like_count)
        """
        logger.debug(f"Getting like status for user {user_id} on recipe {recipe_id}")
        
        liked_by_me = self._mongo.like_check(user_id, recipe_id)
        like_count = self._mongo.like_count_get(recipe_id)
        
        logger.debug(f"Recipe {recipe_id} like status: liked_by_me={liked_by_me}, like_count={like_count}")
        return liked_by_me, like_count
