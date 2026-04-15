import math
import re
import logging

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from app import setup_logger
from app.models.schemas import SearchRequest, SearchResponse, SearchResult
from app.services.embedding_client import OllamaEmbeddingClient
from app.services.llm_client import LLMClient
from app.services.milvus_client import MilvusClient
from app.services.mongo_client import MongoDBClient

# Create module-level logger using centralized setup
logger = setup_logger(__name__, logging.DEBUG)


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


def build_milvus_filter_expr(extracted_fields: Dict[str, Any]) -> Optional[str]:
    """
    Build Milvus filter expression from extracted fields.
    
    Args:
        extracted_fields: Fields extracted by LLM
        
    Returns:
        Milvus filter expression string or None
    """
    filters = []
    
    # Filter by ingredients
    ingredients = extracted_fields.get("ingredients", [])
    if ingredients:
        # Build OR condition for ingredients (any of these ingredients)
        ingredient_filters = []
        for ingredient in ingredients:
            # Escape single quotes in ingredient name
            escaped_ingredient = ingredient.replace("'", "\\'")
            ingredient_filters.append(f"ARRAY_CONTAINS(ingredients, '{escaped_ingredient}')")
        
        if ingredient_filters:
            filters.append(" or ".join(ingredient_filters))
    
    # Filter by tags
    # tags = extracted_fields.get("tags", [])
    # if tags:
    #     tag_filters = []
    #     for tag in tags:
    #         escaped_tag = tag.replace("'", "\\'")
    #         tag_filters.append(f"ARRAY_CONTAINS(tags, '{escaped_tag}')")
        
    #     if tag_filters:
    #         filters.append(" or ".join(tag_filters))
    
    # Filter by cook_time_minutes
    cook_time = extracted_fields.get("cook_time_minutes")
    if cook_time is not None:
        # Assume user wants recipes that can be cooked within this time
        filters.append(f"cook_time_minutes <= {cook_time}")
    
    # Combine all filters with AND
    if filters:
        expr = " and ".join(f"({f})" for f in filters)
        logger.debug(f"Built Milvus filter expression: {expr}")
        return expr
    
    return None


def filter_recipes_by_extracted_fields(
    recipes: List[Dict[str, Any]],
    extracted_fields: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Post-filter recipes based on extracted fields for more precise matching.
    
    Args:
        recipes: List of recipe results from Milvus
        extracted_fields: Fields extracted by LLM
        
    Returns:
        Filtered list of recipes
    """
    filtered = recipes
    
    # Filter by recipe names if specified
    recipe_names = extracted_fields.get("recipe_names", [])
    if recipe_names:
        filtered = [
            r for r in filtered
            if any(name.lower() in r.get("title_zh", "").lower() for name in recipe_names)
        ]
        logger.info(f"Filtered by recipe names: {len(filtered)} results")
    
    # Filter by ingredients (must contain at least one)
    ingredients = extracted_fields.get("ingredients", [])
    if ingredients:
        filtered = [
            r for r in filtered
            if any(
                ingredient.lower() in [ing.lower() for ing in r.get("ingredients", [])]
                for ingredient in ingredients
            )
        ]
        logger.info(f"Filtered by ingredients: {len(filtered)} results")
    
    # Filter by tags (must contain at least one)
    # tags = extracted_fields.get("tags", [])
    # if tags:
    #     filtered = [
    #         r for r in filtered
    #         if any(
    #             tag.lower() in [t.lower() for t in r.get("tags", [])]
    #             for tag in tags
    #         )
    #     ]
    #     logger.info(f"Filtered by tags: {len(filtered)} results")
    
    # Filter by cook time
    # cook_time = extracted_fields.get("cook_time_minutes")
    # if cook_time is not None:
    #     filtered = [
    #         r for r in filtered
    #         if r.get("cook_time_minutes") is not None 
    #         and r.get("cook_time_minutes", 0) <= cook_time
    #     ]
    #     logger.info(f"Filtered by cook time: {len(filtered)} results")
    
    return filtered


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
    llm_client: LLMClient = request.app.state.llm_client
    milvus: MilvusClient = request.app.state.milvus
    mongo: MongoDBClient = request.app.state.mongo
    
    # Get ranking parameters
    alpha = 0.8
    beta = 0.2
    if payload.rank:
        alpha = payload.rank.get("alpha", 0.8)
        beta = payload.rank.get("beta", 0.2)
    
    # LLM-based field extraction (if enabled)
    extracted_fields = {
        "recipe_names": [],
        "ingredients": [],
        "tags": [],
        "cook_time_minutes": None,
        "raw_query": payload.query,
    }
    
    if payload.use_llm_extraction:
        logger.info("Using LLM for field extraction")
        try:
            extracted_fields = await llm_client.extract_search_fields(payload.query)
            logger.info(f"LLM extracted fields: {extracted_fields}")
        except Exception as e:
            logger.error(f"LLM extraction failed, falling back to raw query: {e}")
            # Fallback to original query if LLM fails
            extracted_fields["raw_query"] = payload.query
    
    # Use extracted raw_query for embedding
    search_query = extracted_fields.get("raw_query", payload.query)
    logger.debug(f"Using search query for embedding: {search_query}")
    
    # Generate query embedding
    logger.debug(f"Generating embedding for query: {search_query}")
    query_embedding = await embedding_client.embed(search_query)
    
    # Build Milvus filter expression from extracted fields
    filter_expr = build_milvus_filter_expr(extracted_fields)
    
    # Search in Milvus with larger candidate set for ranking
    candidate_k = max(payload.topK * 5, 20)
    min_similarity = payload.min_similarity or 0.5
    
    logger.debug(f"Searching Milvus with top_k={candidate_k}, min_similarity={min_similarity}, filter_expr={filter_expr}")
    milvus_results = milvus.search_recipes(
        query_embedding=query_embedding,
        top_k=candidate_k,
        expr=filter_expr,
        min_similarity=min_similarity,
    )
    
    if not milvus_results:
        logger.info(f"No results found for query: {payload.query}")
        return SearchResponse(query=payload.query, results=[])
    
    logger.info(f"Found {len(milvus_results)} candidate results from Milvus")
    
    # Post-filter results by extracted fields for more precise matching
    if payload.use_llm_extraction and any([
        extracted_fields.get("recipe_names"),
        extracted_fields.get("ingredients"),
        extracted_fields.get("tags"),
        extracted_fields.get("cook_time_minutes") is not None,
    ]):
        logger.info("Applying post-filtering based on extracted fields")
        milvus_results = filter_recipes_by_extracted_fields(milvus_results, extracted_fields)
        
        if not milvus_results:
            logger.info(f"No results after filtering for query: {payload.query}")
            return SearchResponse(query=payload.query, results=[])
    
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

