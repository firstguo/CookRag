from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import frontmatter

from app.services.embedding_client import OllamaEmbeddingClient
from app.services.mongo_client import MongoDBClient
from app.services.milvus_client import MilvusClient


def slugify(text: str) -> str:
    text = text.strip().lower()
    # Keep ascii alnum and CJK; replace other chars with '-'
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "recipe"


def _normalize_maybe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        # Accept either comma-separated or a single string.
        s = value.strip()
        if not s:
            return []
        if "," in s:
            return [part.strip() for part in s.split(",") if part.strip()]
        return [s]
    return [str(value).strip()]


def _extract_steps_from_body(body: str) -> List[str]:
    """
    Fallback: parse markdown list items like:
      - xxx
      1. xxx
    """
    steps: List[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            steps.append(m.group(1).strip())
            continue
        m = re.match(r"^\d+\.\s+(.+)$", line)
        if m:
            steps.append(m.group(1).strip())
            continue
    return steps


@dataclass
class ParsedRecipe:
    id: str
    title_zh: str
    ingredients: List[str]
    tags: List[str]
    cook_time_minutes: Optional[int]
    steps: List[str]
    content_zh: str
    raw_body: str


def parse_recipe_markdown(path: Path) -> ParsedRecipe:
    post = frontmatter.load(path)
    fm = post.metadata or {}
    body = post.content or ""

    title = str(fm.get("title") or fm.get("title_zh") or "").strip()
    if not title:
        # Use first non-empty line as best-effort fallback.
        for line in body.splitlines():
            if line.strip():
                title = line.strip()
                break
    if not title:
        raise ValueError(f"{path}: missing title")

    rid = str(fm.get("id") or path.stem).strip()
    rid = slugify(rid)

    ingredients = _normalize_maybe_list(fm.get("ingredients"))
    tags = _normalize_maybe_list(fm.get("tags"))

    cook_time_minutes: Optional[int] = None
    if fm.get("cook_time_minutes") is not None:
        try:
            cook_time_minutes = int(fm.get("cook_time_minutes"))
        except ValueError:
            cook_time_minutes = None
    elif fm.get("cook_time") is not None:
        try:
            cook_time_minutes = int(fm.get("cook_time"))
        except ValueError:
            cook_time_minutes = None

    steps = _normalize_maybe_list(fm.get("steps"))
    if not steps:
        steps = _extract_steps_from_body(body)

    # Build embedding text from structured fields; keep it deterministic.
    parts: List[str] = []
    parts.append(f"title: {title}")
    if ingredients:
        parts.append(f"ingredients: {', '.join(ingredients)}")
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    if steps:
        parts.append("steps:\n" + "\n".join([f"- {s}" for s in steps]))
    content_zh = "\n".join(parts).strip()

    return ParsedRecipe(
        id=rid,
        title_zh=title,
        ingredients=ingredients,
        tags=tags,
        cook_time_minutes=cook_time_minutes,
        steps=steps,
        content_zh=content_zh,
        raw_body=body,
    )


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

