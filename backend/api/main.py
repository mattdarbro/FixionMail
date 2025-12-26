"""
FastAPI application for the Storyteller API.

This module sets up the main FastAPI app with routes, middleware,
and configuration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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
# ARCHIVED: Iteration 1 (Long-form interactive story with choices)
# These routes are kept for reference but not loaded in production
# Uncomment if you need to re-enable the interactive story mode
try:
    # from backend.api.routes import router
    # from backend.api.email_choice import router as email_choice_router
    # routes_loaded = True
    routes_loaded = False
    router = None
    email_choice_router = None
    print("ℹ️  Iteration 1 routes (interactive stories) are archived")
except Exception as e:
    print(f"⚠️  Routes loading failed: {e}")
    print("⚠️  API endpoints will not be available, but healthcheck will still work")
    import traceback
    traceback.print_exc()
    router = None
    email_choice_router = None
    routes_loaded = False

# Import FixionMail dev router
try:
    from backend.routes.fictionmail_dev import router as fictionmail_router
    fictionmail_loaded = True
    print("✓ FixionMail dev router imported")
except Exception as e:
    print(f"⚠️  FixionMail dev router loading failed: {e}")
    import traceback
    traceback.print_exc()
    fictionmail_router = None
    fictionmail_loaded = False

# Import Auth routes
try:
    from backend.routes.auth import router as auth_router
    auth_routes_loaded = True
    print("✓ Auth router imported")
except Exception as e:
    print(f"⚠️  Auth router loading failed: {e}")
    auth_router = None
    auth_routes_loaded = False

# Import Stripe webhook routes
try:
    from backend.routes.stripe_webhooks import router as stripe_router
    stripe_routes_loaded = True
    print("✓ Stripe router imported")
except Exception as e:
    print(f"⚠️  Stripe router loading failed: {e}")
    stripe_router = None
    stripe_routes_loaded = False

# Import User routes
try:
    from backend.routes.users import router as users_router
    users_routes_loaded = True
    print("✓ Users router imported")
except Exception as e:
    print(f"⚠️  Users router loading failed: {e}")
    users_router = None
    users_routes_loaded = False

# Import Chat routes (Fixion)
try:
    from backend.routes.chat import router as chat_router
    chat_routes_loaded = True
    print("✓ Chat router imported")
except Exception as e:
    print(f"⚠️  Chat router loading failed: {e}")
    chat_router = None
    chat_routes_loaded = False

# Create FastAPI app
app = FastAPI(
    title="Storyteller API",
    description="AI-powered interactive storytelling with RAG and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend access
# Uses config.allowed_origins_list (defaults to ["*"] in dev mode)
_cors_origins = getattr(config, 'allowed_origins_list', ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes if they loaded successfully
# Note: routes_loaded is False because Iteration 1 routes are archived (not a failure)
if routes_loaded and router:
    app.include_router(router, prefix="/api")
    app.include_router(email_choice_router, prefix="/api")  # Email choice handler

# Include FixionMail dev router
if fictionmail_loaded and fictionmail_router:
    app.include_router(fictionmail_router)
    print("✓ FixionMail dev routes registered")
else:
    print("⚠️  Skipping FixionMail dev routes")

# Include Auth routes
if auth_routes_loaded and auth_router:
    app.include_router(auth_router)
    print("✓ Auth routes registered")
else:
    print("⚠️  Skipping Auth routes")

# Include Stripe webhook routes
if stripe_routes_loaded and stripe_router:
    app.include_router(stripe_router)
    print("✓ Stripe routes registered")
else:
    print("⚠️  Skipping Stripe routes")

# Include User routes
if users_routes_loaded and users_router:
    app.include_router(users_router)
    print("✓ Users routes registered")
else:
    print("⚠️  Skipping Users routes")

# Include Chat routes (Fixion)
if chat_routes_loaded and chat_router:
    app.include_router(chat_router)
    print("✓ Chat routes registered")
else:
    print("⚠️  Skipping Chat routes")

# Mount static files for generated media
# Create directories if they don't exist
os.makedirs("./generated_audio", exist_ok=True)
os.makedirs("./generated_images", exist_ok=True)

# Mount the directories
app.mount("/audio", StaticFiles(directory="./generated_audio"), name="audio")
app.mount("/images", StaticFiles(directory="./generated_images"), name="images")

# Mount React app static assets (JS, CSS from Vite build)
react_assets_path = "./frontend/dist/assets"
if os.path.exists(react_assets_path):
    app.mount("/assets", StaticFiles(directory=react_assets_path), name="react_assets")
    print("✓ React app assets mounted at /assets")


# ===== Root Endpoint =====

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect root to login (React app handles auth redirect if already logged in)."""
    return serve_react_app()


@app.get("/landing", response_class=HTMLResponse)
async def landing():
    """Serve the static landing page (for marketing)."""
    landing_path = "./frontend/landing.html"
    if os.path.exists(landing_path):
        with open(landing_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Landing page not found")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "FixionMail API",
        "version": "3.0.0",
        "status": "operational",
        "mode": "Standalone Daily Stories",
        "docs": "/docs",
        "dashboard": "/dev",
        "endpoints": {
            "onboarding": "POST /api/dev/onboarding",
            "generate_story": "POST /api/dev/generate-story (sync, waits for completion)",
            "queue_story": "POST /api/dev/queue-story (async, returns immediately)",
            "job_status": "GET /api/dev/job/{job_id}",
            "job_result": "GET /api/dev/job/{job_id}/result",
            "list_jobs": "GET /api/dev/jobs",
            "rate_story": "POST /api/dev/rate-story",
            "get_bible": "GET /api/dev/bible",
            "reset": "DELETE /api/dev/reset"
        }
    }


@app.get("/dev", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dev dashboard HTML file."""
    dashboard_path = "./frontend/dev-dashboard.html"
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")


# Keep legacy route for backwards compatibility
@app.get("/dev-dashboard.html", response_class=HTMLResponse)
async def serve_dashboard_legacy():
    """Legacy dev dashboard route - redirects to /dev."""
    dashboard_path = "./frontend/dev-dashboard.html"
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/app", response_class=HTMLResponse)
async def serve_app_placeholder():
    """Serve the app placeholder (coming soon) page."""
    placeholder_path = "./frontend/coming-soon.html"
    if os.path.exists(placeholder_path):
        with open(placeholder_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Placeholder page not found")


@app.get("/signup", response_class=HTMLResponse)
async def serve_signup_placeholder():
    """Serve the signup placeholder (coming soon) page."""
    placeholder_path = "./frontend/coming-soon.html"
    if os.path.exists(placeholder_path):
        with open(placeholder_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Placeholder page not found")


# ===== React App Routes (SPA) =====
# These routes serve the React app's index.html for client-side routing

def serve_react_app():
    """Helper to serve the React app's index.html."""
    react_index_path = "./frontend/dist/index.html"
    if os.path.exists(react_index_path):
        with open(react_index_path, "r") as f:
            return f.read()
    else:
        # Fallback to coming-soon if React app not built
        placeholder_path = "./frontend/coming-soon.html"
        if os.path.exists(placeholder_path):
            with open(placeholder_path, "r") as f:
                return f.read()
        raise HTTPException(status_code=404, detail="React app not found. Run 'npm run build' in frontend/")


@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    """Serve the React app for login page."""
    return serve_react_app()


@app.get("/onboarding", response_class=HTMLResponse)
async def serve_onboarding():
    """Serve the React app for onboarding page."""
    return serve_react_app()


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard_app():
    """Serve the React app for dashboard page."""
    return serve_react_app()


@app.get("/auth/callback", response_class=HTMLResponse)
async def serve_auth_callback():
    """Serve the React app for auth callback page."""
    return serve_react_app()


@app.get("/chat", response_class=HTMLResponse)
async def serve_chat():
    """Serve the React app for chat page."""
    return serve_react_app()


@app.get("/stories", response_class=HTMLResponse)
async def serve_stories():
    """Serve the React app for stories page."""
    return serve_react_app()


# Handle apple-touch-icon requests to prevent 404s
@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon():
    """Return 204 No Content for apple icon requests."""
    from fastapi.responses import Response
    return Response(status_code=204)


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
        print(f"✓ Legacy routes (archived): {routes_loaded}")
        print(f"✓ FixionMail dev routes: {fictionmail_loaded}")

        if not config_loaded:
            print("⚠️  WARNING: Config failed to load. Check environment variables.")
            print("⚠️  Health check will pass, but API will not function.")
            return

        if not routes_loaded:
            # This is expected - Iteration 1 routes are archived, FixionMail dev routes handle all endpoints
            pass

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

            # Security status
            print("\n🔐 Security Status:")
            auth_required = getattr(config, 'auth_required', False)
            api_keys = getattr(config, 'api_keys_list', [])
            allowed_origins = getattr(config, 'allowed_origins_list', ['*'])
            dev_mode = getattr(config, 'DEV_MODE', True)

            if dev_mode and not api_keys:
                print("   ⚠️  DEV MODE: Authentication BYPASSED (no API keys configured)")
            else:
                print(f"   ✓ Authentication: ENABLED ({len(api_keys)} API key(s) configured)")

            if '*' in allowed_origins:
                print("   ⚠️  CORS: All origins allowed (configure ALLOWED_ORIGINS for production)")
            else:
                print(f"   ✓ CORS: Restricted to {len(allowed_origins)} origin(s)")

            rate_limit = getattr(config, 'RATE_LIMIT_PER_MINUTE', 10)
            print(f"   Rate limit: {rate_limit} requests/minute")

            # Supabase status
            print("\n🗄️  Database Status:")
            supabase_configured = getattr(config, 'supabase_configured', False)
            if supabase_configured:
                print("   ✓ Supabase: Configured")
            else:
                print("   ⚠️  Supabase: Not configured (auth and database features unavailable)")

            # Stripe status
            print("\n💳 Payment Status:")
            stripe_configured = getattr(config, 'stripe_configured', False)
            if stripe_configured:
                print("   ✓ Stripe: Configured")
            else:
                print("   ⚠️  Stripe: Not configured (subscription features unavailable)")

        except Exception as e:
            print(f"⚠️  Error accessing config: {e}")
        
        print("=" * 60)

        # ARCHIVED: Story graph initialization (Iteration 1)
        # This is only needed for the interactive story mode
        # if routes_loaded:
        #     try:
        #         from backend.api.routes import initialize_story_graph
        #         print("\n📚 Initializing story graph...")
        #         await initialize_story_graph()
        #         print("✓ Story graph initialization complete")
        #     except Exception as e:
        #         print(f"⚠️  Error initializing story graph during startup: {e}")
        print("ℹ️  Story graph (Iteration 1) not loaded - using FixionMail standalone generation")

        # ARCHIVED: Email system from routes.py (Iteration 1)
        # FixionMail will implement its own email integration
        # if routes_loaded:
        #     try:
        #         from backend.api.routes import initialize_email_system
        #         print("\n📧 Initializing email system...")
        #         await initialize_email_system()
        #         print("✓ Email system initialization complete")
        #     except Exception as e:
        #         print(f"⚠️  Error initializing email system during startup: {e}")
        print("ℹ️  Email system will be initialized by FixionMail when needed")

        # Start background story worker for job queue processing
        if os.getenv("ENABLE_STORY_WORKER", "true").lower() == "true":
            try:
                from backend.jobs import start_story_worker
                print("\n🔄 Starting background story worker...")
                await start_story_worker()
                print("✓ Background story worker started (polling for jobs)")
            except Exception as e:
                print(f"⚠️  Error starting story worker: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("ℹ️  Story worker disabled (ENABLE_STORY_WORKER=false)")

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
        # Use PORT env var first (set by Railway), then fall back to config
        api_port = os.getenv('PORT', getattr(config, 'API_PORT', '8000'))
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
        print("FixionMail API Shutting Down...")
        print("=" * 60)

        # Stop background story worker
        try:
            from backend.jobs import stop_story_worker, close_queue
            print("🔄 Stopping background story worker...")
            stop_story_worker()
            await close_queue()
            print("✓ Background story worker stopped")
        except Exception as e:
            print(f"⚠️  Error stopping story worker: {e}")
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
