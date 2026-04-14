from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from app.services.recipe_parser import parse_recipe_markdown, ParsedRecipe
from app.services.embedding_client import OllamaEmbeddingClient
from app.services.mongo_client import MongoDBClient
from app.services.milvus_client import MilvusClient


async def ingest_recipes_from_dir(
    *,
    recipes_dir: Path,
    embedding_client: OllamaEmbeddingClient,
    mongo: MongoDBClient,
    milvus: MilvusClient,
    limit: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Returns: (recipes_processed, embedding_calls)
    """
    # Recursively find all .md files
    md_files = sorted([p for p in recipes_dir.rglob("*.md") if p.is_file()])
    if limit is not None:
        md_files = md_files[: int(limit)]

    if not md_files:
        return (0, 0)

    embedding_calls = 0
    recipes_processed = 0

    for path in md_files:
        try:
            parsed = parse_recipe_markdown(path)

            # Generate embedding
            embedding = await embedding_client.embed(parsed.content_zh)
            embedding_calls += 1

            # Upsert to MongoDB
            mongo.recipe_upsert({
                "recipe_id": parsed.id,
                "title_zh": parsed.title_zh,
                "content_zh": parsed.content_zh,
                "ingredients": parsed.ingredients,
                "tags": parsed.tags,
                "cook_time_minutes": parsed.cook_time_minutes,
                "steps": parsed.steps,
                "like_count": 0,
            })

            # Upsert to Milvus
            milvus.upsert_recipe({
                "recipe_id": parsed.id,
                "title_zh": parsed.title_zh,
                "content_zh": parsed.content_zh,
                "ingredients": parsed.ingredients,
                "tags": parsed.tags,
                "cook_time_minutes": parsed.cook_time_minutes,
                "embedding": embedding,
            })

            recipes_processed += 1
            print(f"Processed: {parsed.title_zh} ({recipes_processed}/{len(md_files)})")
        except Exception as e:
            print(f"Error processing {path}: {e}")
            continue

    return (recipes_processed, embedding_calls)

