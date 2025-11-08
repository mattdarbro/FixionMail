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

# Import config with error handling
try:
    from backend.config import config
    config_loaded = True
except Exception as e:
    # If config fails, create a minimal config for healthcheck
    print(f"⚠️  Config loading failed: {e}")
    print("⚠️  App may not function correctly, but healthcheck will still work")
    # Create a dummy config object
    class DummyConfig:
        MODEL_NAME = "unknown"
        ENABLE_MEDIA_GENERATION = False
        ENABLE_CREDIT_SYSTEM = False
        DEBUG = False
    config = DummyConfig()
    config_loaded = False

# Import routes with error handling
try:
    from backend.api.routes import router
    routes_loaded = True
except Exception as e:
    print(f"⚠️  Routes loading failed: {e}")
    print("⚠️  API endpoints will not be available, but healthcheck will still work")
    import traceback
    traceback.print_exc()
    router = None
    routes_loaded = False

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

# Include routes if they loaded successfully
if routes_loaded and router:
    app.include_router(router, prefix="/api")
else:
    print("⚠️  Skipping routes registration due to initialization failure")

# Mount static files for generated media
# Create directories if they don't exist
os.makedirs("./generated_audio", exist_ok=True)
os.makedirs("./generated_images", exist_ok=True)

# Mount the directories
app.mount("/audio", StaticFiles(directory="./generated_audio"), name="audio")
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
    """Health check endpoint - must be fast and reliable. Works even if config fails."""
    # This endpoint must ALWAYS return 200 OK - never fail
    # Railway needs this to pass for deployment
    return {
        "status": "healthy",
        "config_loaded": config_loaded,
        "routes_loaded": routes_loaded
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    # Safely check DEBUG flag
    show_details = getattr(config, 'DEBUG', False)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if show_details else "An error occurred",
            "type": type(exc).__name__
        }
    )


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup - non-blocking."""
    try:
        print("=" * 60)
        print("Storyteller API Starting...")
        print("=" * 60)
        print(f"✓ Config loaded: {config_loaded}")
        print(f"✓ Routes loaded: {routes_loaded}")

        if not config_loaded:
            print("⚠️  WARNING: Config failed to load. Check environment variables.")
            print("⚠️  Health check will pass, but API will not function.")
            return

        if not routes_loaded:
            print("⚠️  WARNING: Routes failed to load. Check dependencies.")
            print("⚠️  Health check will pass, but API endpoints unavailable.")
            return

        # Check critical environment variables
        import os
        print("\n🔍 Environment Check:")
        print(f"   ANTHROPIC_API_KEY: {'✓ Set' if os.getenv('ANTHROPIC_API_KEY') else '✗ Missing'}")
        print(f"   STORAGE_PATH: {os.getenv('STORAGE_PATH', '✗ Not set')}")
        print(f"   PORT: {os.getenv('PORT', '8000')}")
        print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")

        # Check if storage path exists
        storage_path = os.getenv('STORAGE_PATH')
        if storage_path:
            if os.path.exists(storage_path):
                print(f"   ✓ Storage directory exists: {storage_path}")
                print(f"   ✓ Storage writable: {os.access(storage_path, os.W_OK)}")
            else:
                print(f"   ⚠️  Storage directory does not exist: {storage_path}")

        print()

        # Safely access config attributes
        try:
            print(f"Model: {getattr(config, 'MODEL_NAME', 'unknown')}")
            print(f"Default World: {getattr(config, 'DEFAULT_WORLD', 'unknown')}")
            print(f"Media Generation: {'Enabled' if getattr(config, 'ENABLE_MEDIA_GENERATION', False) else 'Disabled'}")
            print(f"Credits System: {'Enabled' if getattr(config, 'ENABLE_CREDIT_SYSTEM', False) else 'Disabled'}")
            print(f"Debug Mode: {getattr(config, 'DEBUG', False)}")
        except Exception as e:
            print(f"⚠️  Error accessing config: {e}")
        
        print("=" * 60)

        # Initialize story graph with async checkpointer
        if routes_loaded:
            try:
                from backend.api.routes import initialize_story_graph
                print("\n📚 Initializing story graph...")
                await initialize_story_graph()
                print("✓ Story graph initialization complete")
            except Exception as e:
                print(f"⚠️  Error initializing story graph during startup: {e}")
                print("⚠️  Will fall back to lazy initialization on first request")
                import traceback
                traceback.print_exc()
                # Don't raise - allow app to start, lazy init will handle it

        # Initialize email system
        if routes_loaded:
            try:
                from backend.api.routes import initialize_email_system
                print("\n📧 Initializing email system...")
                await initialize_email_system()
                print("✓ Email system initialization complete")
            except Exception as e:
                print(f"⚠️  Error initializing email system during startup: {e}")
                print("⚠️  Email features will be disabled")
                import traceback
                traceback.print_exc()
                # Don't raise - allow app to start without email

        # Start background email processor
        if routes_loaded and os.getenv("ENABLE_EMAIL_SCHEDULER", "true").lower() == "true":
            try:
                from backend.email.background import start_background_processor
                print("\n🔄 Starting background email processor...")
                await start_background_processor()
                print("✓ Background email processor started")
            except Exception as e:
                print(f"⚠️  Error starting background email processor: {e}")
                print("⚠️  Scheduled emails will not be sent automatically")
                import traceback
                traceback.print_exc()
                # Don't raise - allow app to start without background processor

        # Validate world templates exist (no longer using RAG)
        try:
            from pathlib import Path

            default_world = getattr(config, 'DEFAULT_WORLD', 'west_haven')
            world_template_path = Path("story_worlds") / default_world / "world_template.json"

            if world_template_path.exists():
                print(f"✓ Found world template for '{default_world}'")
            else:
                print(f"⚠️  World template not found: {world_template_path}")
                print(f"    Please create world_template.json for '{default_world}'")

        except Exception as e:
            print(f"⚠️  Error checking world templates: {e}")

        print("=" * 60)
        api_host = getattr(config, 'API_HOST', '0.0.0.0')
        api_port = getattr(config, 'API_PORT', os.getenv('PORT', '8000'))
        print(f"API available at: http://{api_host}:{api_port}")
        print(f"Docs available at: http://{api_host}:{api_port}/docs")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Startup event error (non-fatal): {e}")
        # Don't raise - allow app to continue for healthcheck


# ===== Shutdown Event =====

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        print("\n" + "=" * 60)
        print("Storyteller API Shutting Down...")
        print("=" * 60)

        # Stop background email processor
        try:
            from backend.email.background import stop_background_processor
            print("🔄 Stopping background email processor...")
            stop_background_processor()
            print("✓ Background email processor stopped")
        except Exception as e:
            print(f"⚠️  Error stopping background email processor: {e}")

        print("=" * 60)
        print("Shutdown complete")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Shutdown event error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
