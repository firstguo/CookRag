import math
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app import setup_logger
from app.models.schemas import SearchRequest, SearchResponse, SearchResult
from app.services.embedding_client import OllamaEmbeddingClient
from app.services.milvus_client import MilvusClient
from app.services.mongo_client import MongoDBClient

# Create module-level logger using centralized setup
logger = setup_logger(__name__)


router = APIRouter()


def validate_chinese_query(query: str) -> bool:
    """Check if query contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', query))


def calculate_final_score(score: float, like_count: int, max_like_count: int, alpha: float = 0.8, beta: float = 0.2) -> float:
    """Calculate final score using hybrid ranking."""
    # Normalize like_count using log normalization
    if max_like_count > 0:
        like_norm = math.log(1 + like_count) / math.log(1 + max_like_count)
    else:
        like_norm = 0.0
    
    # Final score: alpha * score + beta * like_norm
    return alpha * score + beta * like_norm


@router.post("/api/search", response_model=SearchResponse)
async def search_recipes(payload: SearchRequest, request: Request) -> SearchResponse:
    logger.info(f"Search requested for query: {payload.query}")
    
    # Validate Chinese query
    if not validate_chinese_query(payload.query):
        logger.warning(f"Search query does not contain Chinese characters: {payload.query}")
        raise HTTPException(
            status_code=400,
            detail="Query must contain Chinese characters",
        )
    
    embedding_client: OllamaEmbeddingClient = request.app.state.embedding_client
    milvus: MilvusClient = request.app.state.milvus
    mongo: MongoDBClient = request.app.state.mongo
    
    # Get ranking parameters
    alpha = 0.8
    beta = 0.2
    if payload.rank:
        alpha = payload.rank.get("alpha", 0.8)
        beta = payload.rank.get("beta", 0.2)
    
    # Generate query embedding
    logger.debug(f"Generating embedding for query: {payload.query}")
    query_embedding = await embedding_client.embed(payload.query)
    
    # Search in Milvus with larger candidate set for ranking
    candidate_k = max(payload.topK * 5, 20)
    logger.debug(f"Searching Milvus with top_k={candidate_k}")
    milvus_results = milvus.search_recipes(
        query_embedding=query_embedding,
        top_k=candidate_k,
    )
    
    if not milvus_results:
        logger.info(f"No results found for query: {payload.query}")
        return SearchResponse(query=payload.query, results=[])
    
    logger.info(f"Found {len(milvus_results)} candidate results for query: {payload.query}")
    
    # Get recipe IDs from Milvus results
    recipe_ids = [r["recipe_id"] for r in milvus_results]
    
    # Fetch full recipe data from MongoDB (including like_count)
    mongo_recipes = mongo.recipe_get_by_ids(recipe_ids)
    mongo_dict = {r["recipe_id"]: r for r in mongo_recipes}
    
    # Find max like_count for normalization
    max_like_count = max(
        (mongo_dict.get(rid, {}).get("like_count", 0) for rid in recipe_ids),
        default=0
    )
    
    # Combine Milvus scores with MongoDB like_counts
    combined_results = []
    for milvus_result in milvus_results:
        recipe_id = milvus_result["recipe_id"]
        mongo_recipe = mongo_dict.get(recipe_id, {})
        like_count = mongo_recipe.get("like_count", 0)
        
        # Calculate final score
        final_score = calculate_final_score(
            score=milvus_result["score"],
            like_count=like_count,
            max_like_count=max_like_count,
            alpha=alpha,
            beta=beta,
        )
        
        # Create snippet from content_zh (first 200 chars)
        content_zh = milvus_result.get("content_zh", "")
        snippet = content_zh[:200] if len(content_zh) > 200 else content_zh
        
        combined_results.append(SearchResult(
            id=recipe_id,
            title_zh=milvus_result["title_zh"],
            score=milvus_result["score"],
            like_count=like_count,
            final_score=final_score,
            snippet=snippet if snippet else None,
        ))
    
    # Sort by final_score descending and limit to topK
    combined_results.sort(key=lambda x: x.final_score, reverse=True)
    combined_results = combined_results[:payload.topK]
    
    logger.info(f"Returning {len(combined_results)} results for query: {payload.query}")
    return SearchResponse(query=payload.query, results=combined_results)

