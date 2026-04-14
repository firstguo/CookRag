from __future__ import annotations

from typing import Any, Dict, List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import Settings


class MilvusClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._collection_name = settings.MILVUS_COLLECTION_NAME
        
        # Connect to Milvus
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        
        # Initialize collection
        self._collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self) -> Collection:
        """Get existing collection or create new one."""
        if utility.has_collection(self._collection_name):
            return Collection(name=self._collection_name)
        
        # Define schema
        fields = [
            FieldSchema(
                name="recipe_id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(
                name="title_zh",
                dtype=DataType.VARCHAR,
                max_length=256,
            ),
            FieldSchema(
                name="content_zh",
                dtype=DataType.VARCHAR,
                max_length=4096,
            ),
            FieldSchema(
                name="ingredients",
                dtype=DataType.ARRAY,
                element_type=DataType.VARCHAR,
                max_length=128,
                max_capacity=50,
            ),
            FieldSchema(
                name="tags",
                dtype=DataType.ARRAY,
                element_type=DataType.VARCHAR,
                max_length=64,
                max_capacity=20,
            ),
            FieldSchema(
                name="cook_time_minutes",
                dtype=DataType.INT32,
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=1024,  # bge-m3 dimension
            ),
        ]
        
        schema = CollectionSchema(
            fields,
            description="Recipe vector index with metadata",
        )
        
        collection = Collection(name=self._collection_name, schema=schema)
        
        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        
        return collection
    
    def close(self) -> None:
        """Disconnect from Milvus."""
        connections.disconnect("default")
    
    def upsert_recipe(self, recipe: Dict[str, Any]) -> None:
        """Upsert a recipe into Milvus collection."""
        # Prepare data for upsert
        data = [{
            "recipe_id": recipe["recipe_id"],
            "title_zh": recipe.get("title_zh", ""),
            "content_zh": recipe.get("content_zh", ""),
            "ingredients": recipe.get("ingredients", []),
            "tags": recipe.get("tags", []),
            "cook_time_minutes": recipe.get("cook_time_minutes") or 0,
            "embedding": recipe["embedding"],
        }]
        
        # Delete existing record if exists
        if self._collection.num_entities > 0:
            self._collection.delete(f"recipe_id == '{recipe['recipe_id']}'")
            self._collection.flush()
        
        # Insert new data
        self._collection.insert(data)
        self._collection.flush()
    
    def search_recipes(
        self,
        query_embedding: List[float],
        top_k: int = 8,
        expr: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search recipes by vector similarity.
        
        Args:
            query_embedding: The query embedding vector
            top_k: Number of results to return
            expr: Optional filter expression (e.g., "array_contains(ingredients, '鸡蛋')")
        
        Returns:
            List of search results with metadata
        """
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64},
        }
        
        results = self._collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=[
                "recipe_id",
                "title_zh",
                "content_zh",
                "ingredients",
                "tags",
                "cook_time_minutes",
            ],
        )
        
        # Parse results
        recipes = []
        for hits in results:
            for hit in hits:
                recipes.append({
                    "recipe_id": hit.entity.get("recipe_id"),
                    "title_zh": hit.entity.get("title_zh"),
                    "content_zh": hit.entity.get("content_zh"),
                    "ingredients": hit.entity.get("ingredients", []),
                    "tags": hit.entity.get("tags", []),
                    "cook_time_minutes": hit.entity.get("cook_time_minutes"),
                    "score": float(hit.distance),
                })
        
        return recipes
    
    def delete_recipe(self, recipe_id: str) -> None:
        """Delete a recipe from Milvus collection."""
        self._collection.delete(f"recipe_id == '{recipe_id}'")
        self._collection.flush()
    
    def collection_exists(self) -> bool:
        """Check if collection exists."""
        return utility.has_collection(self._collection_name)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "name": self._collection_name,
            "num_entities": self._collection.num_entities,
        }
