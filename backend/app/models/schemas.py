from typing import Any, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    topK: int = Field(default=8, ge=1, le=50)
    # Ranking parameters
    rank: Optional[dict[str, float]] = Field(
        default=None,
        description="Ranking weights: {alpha: 0.8, beta: 0.2}",
    )
    # Minimum similarity threshold (0.0-1.0)
    min_similarity: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold for results",
    )
    # Enable LLM-based field extraction
    use_llm_extraction: bool = Field(
        default=True,
        description="Use LLM to extract fields and filter results",
    )


class SearchResult(BaseModel):
    id: str
    title_zh: str
    score: float
    like_count: int = 0
    final_score: float
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


class RecipeOut(BaseModel):
    id: str
    title_zh: str
    ingredients: List[str] = []
    tags: List[str] = []
    cook_time_minutes: Optional[int] = None
    content_zh: str
    steps: List[str] = []
    like_count: int = 0
    liked_by_me: bool = False
    meta: Optional[dict[str, Any]] = None


# Auth schemas
class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    nickname: str
    password: str


class UserResponse(BaseModel):
    id: str
    nickname: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class RegisterResponse(BaseModel):
    user: UserResponse


class LikeResponse(BaseModel):
    liked_by_me: bool
    like_count: int

