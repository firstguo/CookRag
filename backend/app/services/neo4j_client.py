from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase

from app.config import Settings


class Neo4jClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

    async def close(self) -> None:
        await self._driver.close()

    async def recipe_get(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Recipe {id: $id})
                RETURN
                  r.id AS id,
                  r.title_zh AS title_zh,
                  coalesce(r.ingredients, []) AS ingredients,
                  coalesce(r.tags, []) AS tags,
                  r.cook_time_minutes AS cook_time_minutes,
                  r.content_zh AS content_zh,
                  coalesce(r.steps, []) AS steps
                """,
                {"id": recipe_id},
            )
            row = await result.single()
            return dict(row) if row else None

    async def search_recipes(
        self,
        *,
        index_name: str,
        query_embedding: List[float],
        top_k: int,
        with_snippet: bool = False,
    ) -> List[Dict[str, Any]]:
        async with self._driver.session() as session:
            # Neo4j returns cosine similarity score in [0, 1] for cosine.
            cypher = f"""
                CALL db.index.vector.queryNodes('{index_name}', $k, $embedding)
                YIELD node AS recipe, score
                RETURN
                  recipe.id AS id,
                  recipe.title_zh AS title_zh,
                  score AS score
                  {", substring(recipe.content_zh, 0, 200) AS snippet" if with_snippet else ""}
                ORDER BY score DESC
                LIMIT $k
            """
            params = {
                "k": int(top_k),
                "embedding": query_embedding,
            }
            result = await session.run(cypher, params)
            rows = await result.to_list()
            return [dict(r) for r in rows]

    async def create_vector_index_if_missing(
        self,
        *,
        index_name: str,
        dimensions: int,
        similarity_function: str = "cosine",
        label: str = "Recipe",
        embedding_property: str = "embedding",
    ) -> None:
        """
        Create a Neo4j vector index if it doesn't exist.
        Note: avoid changing dimensions after the index is created.
        """
        async with self._driver.session() as session:
            idx_rows = await session.run(
                """
                CALL db.indexes()
                YIELD name, type, labelsOrTypes, properties
                WHERE name = $name
                RETURN name, type, labelsOrTypes, properties
                """,
                {"name": index_name},
            )

    async def recipe_upsert(
        self,
        *,
        recipe: Dict[str, Any],
    ) -> None:
        """
        Upsert a recipe node by id.

        Expected keys:
          - id (str)
          - title_zh (str)
          - content_zh (str)
          - ingredients (List[str])
          - tags (List[str])
          - cook_time_minutes (int|None)
          - steps (List[str])
          - embedding (List[float])
        """
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (r:Recipe {id: $id})
                SET
                  r.title_zh = $title_zh,
                  r.content_zh = $content_zh,
                  r.ingredients = $ingredients,
                  r.tags = $tags,
                  r.cook_time_minutes = $cook_time_minutes,
                  r.steps = $steps,
                  r.embedding = $embedding
                """,
                {
                    "id": recipe["id"],
                    "title_zh": recipe["title_zh"],
                    "content_zh": recipe["content_zh"],
                    "ingredients": recipe.get("ingredients", []),
                    "tags": recipe.get("tags", []),
                    "cook_time_minutes": recipe.get("cook_time_minutes"),
                    "steps": recipe.get("steps", []),
                    "embedding": recipe["embedding"],
                },
            )
            existing = await idx_rows.single()
            if existing:
                return

            # Neo4j vector index creation (Neo4j 5.x).
            await session.run(
                f"""
                CREATE VECTOR INDEX {index_name}
                IF NOT EXISTS
                FOR (n:{label})
                ON (n.{embedding_property})
                OPTIONS {{
                  indexConfig: {{
                    `vector.dimensions`: $dimensions,
                    `vector.similarity_function`: $similarity_function
                  }}
                }}
                """,
                {"dimensions": int(dimensions), "similarity_function": similarity_function},
            )

