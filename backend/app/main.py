from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
        # Store shared clients on app.state so route handlers remain thin.
        app.state.settings = settings
        app.state.embedding_client = OllamaEmbeddingClient(settings)
        app.state.mongo = MongoDBClient(settings)
        app.state.milvus = MilvusClient(settings)
        app.state.auth_service = AuthService(settings)
        app.state.like_service = LikeService(app.state.mongo)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        mongo: MongoDBClient | None = getattr(app.state, "mongo", None)
        if mongo:
            mongo.close()
        
        milvus: MilvusClient | None = getattr(app.state, "milvus", None)
        if milvus:
            milvus.close()
    
    # Health check endpoints
    @app.get("/healthz")
    async def healthz():
        """Basic health check."""
        return {"status": "ok"}
    
    @app.get("/readyz")
    async def readyz():
        """Readiness check - verifies all services are connected."""
        try:
            # Check MongoDB
            mongo: MongoDBClient = app.state.mongo
            mongo._client.admin.command('ping')
            
            # Check Milvus
            milvus: MilvusClient = app.state.milvus
            milvus.collection_exists()
            
            # Check Ollama (basic connectivity)
            embedding_client: OllamaEmbeddingClient = app.state.embedding_client
            
            return {
                "status": "ready",
                "mongodb": "connected",
                "milvus": "connected",
                "ollama": "connected",
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "error": str(e)},
            )

    return app


app = create_app()

