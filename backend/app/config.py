import os
from typing import List


def _split_env(name: str, default: str = "") -> List[str]:
    value = os.getenv(name, default).strip()
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    # Server
    APP_NAME: str = os.getenv("APP_NAME", "CookRag")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ALLOW_ORIGINS: List[str] = _split_env("CORS_ALLOW_ORIGINS", "http://localhost:5173")

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "cookrag")

    # Milvus
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "recipes")

    # Ollama embeddings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
    OLLAMA_TIMEOUT_S: float = float(os.getenv("OLLAMA_TIMEOUT_S", "120"))

    # LLM Configuration (LangChain-based)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "qwen")  # Options: "qwen", "deepseek", "ollama"
    
    # Qwen/Tongyi Qianwen API
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "sk-699ba77b0983413786edce60125dad93")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen3-max-2026-01-23")
    
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Ollama LLM (fallback)
    OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")

    # Vector index
    VECTOR_INDEX_NAME: str = os.getenv("VECTOR_INDEX_NAME", "recipes")

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cookrag123")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

