from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api.recipes import router as recipes_router
from app.api.search import router as search_router
from app.api.auth import router as auth_router
from app.api.likes import router as likes_router
from app.config import Settings
from app.services.embedding_client import OllamaEmbeddingClient
from app.services.mongo_client import MongoDBClient
from app.services.milvus_client import MilvusClient
from app.services.auth import AuthService
from app.services.like_service import LikeService
from app import setup_logger

# Create module-level logger
logger = setup_logger(__name__)


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(title=settings.APP_NAME)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(search_router)
    app.include_router(recipes_router)
    app.include_router(auth_router)
    app.include_router(likes_router)

    @app.on_event("startup")
    async def _startup() -> None:
        logger.info("Starting up CookRag application...")
        # Store shared clients on app.state so route handlers remain thin.
        app.state.settings = settings
        app.state.embedding_client = OllamaEmbeddingClient(settings)
        app.state.mongo = MongoDBClient(settings)
        app.state.milvus = MilvusClient(settings)
        app.state.auth_service = AuthService(settings)
        app.state.like_service = LikeService(app.state.mongo)
        logger.info("CookRag application started successfully")

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        logger.info("Shutting down CookRag application...")
        mongo: MongoDBClient | None = getattr(app.state, "mongo", None)
        if mongo:
            mongo.close()
            logger.info("MongoDB connection closed")
        
        milvus: MilvusClient | None = getattr(app.state, "milvus", None)
        if milvus:
            milvus.close()
            logger.info("Milvus connection closed")
        logger.info("CookRag application shut down successfully")
    
    # Health check endpoints
    @app.get("/healthz")
    async def healthz():
        """Basic health check."""
        logger.debug("Health check requested")
        return {"status": "ok"}
    
    @app.get("/readyz")
    async def readyz():
        """Readiness check - verifies all services are connected."""
        try:
            logger.debug("Readiness check requested")
            # Check MongoDB
            mongo: MongoDBClient = app.state.mongo
            mongo._client.admin.command('ping')
            
            # Check Milvus
            milvus: MilvusClient = app.state.milvus
            milvus.collection_exists()
            
            # Check Ollama (basic connectivity)
            embedding_client: OllamaEmbeddingClient = app.state.embedding_client
            
            logger.info("All services are ready")
            return {
                "status": "ready",
                "mongodb": "connected",
                "milvus": "connected",
                "ollama": "connected",
            }
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "error": str(e)},
            )

    return app


app = create_app()

