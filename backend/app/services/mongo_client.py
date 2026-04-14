from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from app.config import Settings


class MongoDBClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = MongoClient(settings.MONGODB_URI)
        self._db = self._client[settings.MONGODB_DB_NAME]
        
        # Collections
        self._recipes = self._db["recipes"]
        self._users = self._db["users"]
        self._recipe_likes = self._db["recipe_likes"]
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for collections."""
        self._recipes.create_index("recipe_id", unique=True)
        self._recipes.create_index("tags")
        
        self._users.create_index("nickname", unique=True)
        self._users.create_index("user_id", unique=True)
        
        self._recipe_likes.create_index(
            [("user_id", 1), ("recipe_id", 1)], unique=True
        )
        self._recipe_likes.create_index("recipe_id")
    
    def close(self) -> None:
        self._client.close()
    
    # Recipe operations
    def recipe_upsert(self, recipe: Dict[str, Any]) -> None:
        """Upsert a recipe by recipe_id."""
        now = datetime.now(timezone.utc)
        recipe["updated_at"] = now
        
        if "created_at" not in recipe:
            recipe["created_at"] = now
        
        if "like_count" not in recipe:
            recipe["like_count"] = 0
        
        self._recipes.update_one(
            {"recipe_id": recipe["recipe_id"]},
            {"$set": recipe},
            upsert=True
        )
    
    def recipe_get(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get a recipe by recipe_id."""
        doc = self._recipes.find_one({"recipe_id": recipe_id})
        if not doc:
            return None
        
        # Convert ObjectId to string for JSON serialization
        doc["id"] = doc.pop("_id")
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    def recipe_get_by_ids(self, recipe_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple recipes by their IDs."""
        cursor = self._recipes.find({"recipe_id": {"$in": recipe_ids}})
        results = []
        for doc in cursor:
            doc["id"] = doc.pop("_id")
            results.append(doc)
        return results
    
    def recipe_update_like_count(self, recipe_id: str, increment: int) -> None:
        """Update like_count for a recipe."""
        self._recipes.update_one(
            {"recipe_id": recipe_id},
            {"$inc": {"like_count": increment}}
        )
    
    # User operations
    def user_create(self, nickname: str, password_hash: str) -> Dict[str, Any]:
        """Create a new user."""
        import uuid
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        user_doc = {
            "user_id": user_id,
            "nickname": nickname,
            "password_hash": password_hash,
            "created_at": now,
        }
        
        try:
            self._users.insert_one(user_doc)
            return {
                "id": user_id,
                "nickname": nickname,
            }
        except DuplicateKeyError:
            raise ValueError("Nickname already exists")
    
    def user_get_by_nickname(self, nickname: str) -> Optional[Dict[str, Any]]:
        """Get user by nickname."""
        return self._users.find_one({"nickname": nickname})
    
    # Like operations
    def like_add(self, user_id: str, recipe_id: str) -> bool:
        """Add a like. Returns True if added, False if already exists."""
        try:
            now = datetime.now(timezone.utc)
            self._recipe_likes.insert_one({
                "user_id": user_id,
                "recipe_id": recipe_id,
                "created_at": now,
            })
            return True
        except DuplicateKeyError:
            return False
    
    def like_remove(self, user_id: str, recipe_id: str) -> bool:
        """Remove a like. Returns True if removed, False if not exists."""
        result = self._recipe_likes.delete_one({
            "user_id": user_id,
            "recipe_id": recipe_id,
        })
        return result.deleted_count > 0
    
    def like_check(self, user_id: str, recipe_id: str) -> bool:
        """Check if user has liked a recipe."""
        return self._recipe_likes.find_one({
            "user_id": user_id,
            "recipe_id": recipe_id,
        }) is not None
    
    def like_count_get(self, recipe_id: str) -> int:
        """Get like count for a recipe."""
        doc = self._recipes.find_one(
            {"recipe_id": recipe_id},
            {"like_count": 1}
        )
        return doc.get("like_count", 0) if doc else 0
