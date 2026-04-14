import argparse
import asyncio
import sys
from pathlib import Path


def _bootstrap_imports() -> None:
    """
    Allow running `python backend/scripts/ingest.py` from repo root.
    """
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))


_bootstrap_imports()

from app.config import Settings  # noqa: E402
from app.services.embedding_client import OllamaEmbeddingClient  # noqa: E402
from app.services.mongo_client import MongoDBClient  # noqa: E402
from app.services.milvus_client import MilvusClient  # noqa: E402
from app.services.recipe_ingest import ingest_recipes_from_dir  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipes-dir", default="recipes", help="Path to recipes markdown directory")
    parser.add_argument("--limit", type=int, default=None, help="Ingest only first N recipes")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    recipes_dir = (repo_root / args.recipes_dir).resolve()
    if not recipes_dir.exists():
        raise SystemExit(f"recipes dir not found: {recipes_dir}")

    settings = Settings()
    embedding_client = OllamaEmbeddingClient(settings)
    mongo = MongoDBClient(settings)
    milvus = MilvusClient(settings)

    try:
        processed, embedding_calls = await ingest_recipes_from_dir(
            recipes_dir=recipes_dir,
            embedding_client=embedding_client,
            mongo=mongo,
            milvus=milvus,
            limit=args.limit,
        )
        print(f"Ingest finished. recipes_processed={processed}, embedding_calls={embedding_calls}")
    finally:
        mongo.close()
        milvus.close()


if __name__ == "__main__":
    asyncio.run(main())

