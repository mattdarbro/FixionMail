"""
FastAPI application for the Storyteller API.

This module sets up the main FastAPI app with routes, middleware,
and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.config import config
from backend.api.routes import router

# Create FastAPI app
app = FastAPI(
    title="Storyteller API",
    description="AI-powered interactive storytelling with RAG and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")

# Mount static files for generated media
if os.path.exists("./generated_audio"):
    app.mount("/audio", StaticFiles(directory="./generated_audio"), name="audio")

if os.path.exists("./generated_images"):
    app.mount("/images", StaticFiles(directory="./generated_images"), name="images")


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Storyteller API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "start_story": "POST /api/story/start",
            "continue_story": "POST /api/story/continue",
            "get_session": "GET /api/story/session/{session_id}",
            "list_worlds": "GET /api/worlds"
        }
    }


# ===== Health Check =====

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "config": {
            "model": config.MODEL_NAME,
            "rag_enabled": True,
            "media_generation": config.ENABLE_MEDIA_GENERATION,
            "credits_enabled": config.ENABLE_CREDIT_SYSTEM
        }
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.DEBUG else "An error occurred",
            "type": type(exc).__name__
        }
    )


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("=" * 60)
    print("Storyteller API Starting...")
    print("=" * 60)
    print(f"Model: {config.MODEL_NAME}")
    print(f"Default World: {config.DEFAULT_WORLD}")
    print(f"Media Generation: {'Enabled' if config.ENABLE_MEDIA_GENERATION else 'Disabled'}")
    print(f"Credits System: {'Enabled' if config.ENABLE_CREDIT_SYSTEM else 'Disabled'}")
    print(f"Debug Mode: {config.DEBUG}")
    print("=" * 60)

    # Initialize story worlds in background (don't block startup)
    # This allows healthcheck to pass even if RAG loading takes time
    import asyncio
    from backend.story_bible.rag import StoryWorldFactory

    def load_world_sync():
        """Synchronous RAG loading function."""
        try:
            # Load default world
            rag = StoryWorldFactory.get_world(config.DEFAULT_WORLD, auto_load=True)
            stats = rag.get_collection_stats()

            if "error" in stats:
                print(f"⚠️  Default world '{config.DEFAULT_WORLD}' not indexed yet")
                print(f"    Run: python scripts/init_rag.py {config.DEFAULT_WORLD}")
            else:
                print(f"✓ Loaded world '{config.DEFAULT_WORLD}'")
                print(f"  Documents: {stats.get('document_count', 'unknown')}")

        except Exception as e:
            print(f"⚠️  Error loading default world: {e}")

    # Run RAG loading in background thread (non-blocking)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, load_world_sync)

    print("=" * 60)
    print(f"API available at: http://{config.API_HOST}:{config.API_PORT}")
    print(f"Docs available at: http://{config.API_HOST}:{config.API_PORT}/docs")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
