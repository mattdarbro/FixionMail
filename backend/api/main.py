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

# Import Stories routes
try:
    from backend.routes.stories import router as stories_router
    stories_routes_loaded = True
    print("✓ Stories router imported")
except Exception as e:
    print(f"⚠️  Stories router loading failed: {e}")
    stories_router = None
    stories_routes_loaded = False

# Import Admin routes
try:
    from backend.routes.admin import router as admin_router
    admin_routes_loaded = True
    print("✓ Admin router imported")
except Exception as e:
    print(f"⚠️  Admin router loading failed: {e}")
    admin_router = None
    admin_routes_loaded = False

# Import Pre-Show routes (iOS app)
try:
    from backend.routes.preshow import router as preshow_router
    preshow_routes_loaded = True
    print("✓ Pre-show router imported")
except Exception as e:
    print(f"⚠️  Pre-show router loading failed: {e}")
    preshow_router = None
    preshow_routes_loaded = False

# Import Device routes (iOS app push notifications)
try:
    from backend.routes.devices import router as devices_router
    devices_routes_loaded = True
    print("✓ Devices router imported")
except Exception as e:
    print(f"⚠️  Devices router loading failed: {e}")
    devices_router = None
    devices_routes_loaded = False

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

# Include Stories routes
if stories_routes_loaded and stories_router:
    app.include_router(stories_router)
    print("✓ Stories routes registered")
else:
    print("⚠️  Skipping Stories routes")

# Include Admin routes
if admin_routes_loaded and admin_router:
    app.include_router(admin_router)
    print("✓ Admin routes registered")
else:
    print("⚠️  Skipping Admin routes")

# Include Pre-Show routes (iOS app)
if preshow_routes_loaded and preshow_router:
    app.include_router(preshow_router)
    print("✓ Pre-show routes registered")
else:
    print("⚠️  Skipping Pre-show routes")

# Include Device routes (iOS app push notifications)
if devices_routes_loaded and devices_router:
    app.include_router(devices_router)
    print("✓ Devices routes registered")
else:
    print("⚠️  Skipping Devices routes")

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
        "admin": "/admin",
        "endpoints": {
            "onboarding": "POST /api/dev/onboarding",
            "generate_story": "POST /api/dev/generate-story (sync, waits for completion)",
            "queue_story": "POST /api/dev/queue-story (async, returns immediately)",
            "job_status": "GET /api/dev/job/{job_id}",
            "job_result": "GET /api/dev/job/{job_id}/result",
            "list_jobs": "GET /api/dev/jobs",
            "rate_story": "POST /api/dev/rate-story",
            "get_bible": "GET /api/dev/bible",
            "reset": "DELETE /api/dev/reset",
            "admin_overview": "GET /api/admin/overview",
            "admin_users": "GET /api/admin/users",
            "admin_stories": "GET /api/admin/stories",
            "admin_scheduled": "GET /api/admin/scheduled",
            "admin_jobs": "GET /api/admin/jobs",
            "admin_logs": "GET /api/admin/logs"
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


@app.get("/library", response_class=HTMLResponse)
async def serve_library():
    """Serve the story library page."""
    library_path = "./frontend/library.html"
    if os.path.exists(library_path):
        with open(library_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Library not found")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_dashboard():
    """Serve the admin dashboard for system monitoring."""
    admin_path = "./frontend/admin-dashboard.html"
    if os.path.exists(admin_path):
        with open(admin_path, "r") as f:
            return f.read()
    else:
        raise HTTPException(status_code=404, detail="Admin dashboard not found")


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


@app.get("/api/status")
async def system_status():
    """System status endpoint - shows queue depth, worker status, and delivery stats."""
    from datetime import datetime, timezone

    queue_stats = {"pending": 0, "running": 0, "completed_today": 0, "failed_today": 0}
    delivery_stats = {"pending": 0, "sent_today": 0, "failed": 0}
    redis_stats = None

    try:
        from backend.database.jobs import JobQueueService
        from backend.database.deliveries import DeliveryService

        # Job queue stats from Supabase
        job_service = JobQueueService()
        job_stats = await job_service.get_queue_stats()
        queue_stats["pending"] = job_stats.get("pending", 0)
        queue_stats["running"] = job_stats.get("running", 0)
        queue_stats["completed_today"] = job_stats.get("completed", 0)
        queue_stats["failed_today"] = job_stats.get("failed", 0)

        # Delivery stats from Supabase
        delivery_service = DeliveryService()
        del_stats = await delivery_service.get_delivery_stats()
        delivery_stats["pending"] = del_stats.get("pending", 0)
        delivery_stats["sent_today"] = del_stats.get("sent_today", 0)
        delivery_stats["failed"] = del_stats.get("failed", 0)
        delivery_stats["upcoming_1h"] = del_stats.get("upcoming_1h", 0)

    except Exception as e:
        queue_stats["error"] = str(e)

    # Redis queue stats (if enabled)
    if config.redis_configured:
        try:
            from backend.queue.connection import redis_health_check
            redis_stats = redis_health_check()
        except Exception as e:
            redis_stats = {"status": "error", "error": str(e)}

    worker_mode = "redis_queue" if config.redis_configured else "apscheduler"

    return {
        "status": "operational",
        "mode": worker_mode,
        "queue": queue_stats,
        "deliveries": delivery_stats,
        "redis": redis_stats,
        "workers": {
            "story_worker": "Redis Queue" if config.redis_configured else "APScheduler (in-process)",
            "delivery_worker": "Redis Queue" if config.redis_configured else "APScheduler (in-process)"
        },
        "capacity": "scalable" if config.redis_configured else "~6 stories/hour"
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

        # ===== Background Workers =====
        # In Redis Queue mode, workers run as separate processes (not in the web process)
        # In single-process mode (default), workers run in-process via APScheduler
        #
        # IMPORTANT: Check REDIS_URL directly - if it's set, assume Redis mode is intended
        # This prevents duplicate story generation when both web server and separate
        # scheduler/worker services are running

        redis_queue_mode = bool(config.REDIS_URL)

        if redis_queue_mode:
            print("\n🔴 Redis Queue Mode (REDIS_URL is set)")
            print("   Workers should run as separate processes:")
            print("   - SERVICE_TYPE=worker (story generation + email sending)")
            print("   - SERVICE_TYPE=scheduler (daily story scheduling)")
            print("   - SERVICE_TYPE=delivery (email delivery scheduling)")
            print("   In-process APScheduler workers are DISABLED to prevent duplicates")
        else:
            print("\n🟢 Single-Process Mode (APScheduler)")
            print("   Workers run in-process within this web server")

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

            # Start daily story scheduler
            if os.getenv("ENABLE_DAILY_SCHEDULER", "true").lower() == "true":
                try:
                    from backend.jobs import start_daily_scheduler
                    print("\n📅 Starting daily story scheduler...")
                    await start_daily_scheduler()
                    print("✓ Daily story scheduler started (checking delivery times)")
                except Exception as e:
                    print(f"⚠️  Error starting daily scheduler: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("ℹ️  Daily scheduler disabled (ENABLE_DAILY_SCHEDULER=false)")

            # Start email delivery worker
            if os.getenv("ENABLE_DELIVERY_WORKER", "true").lower() == "true":
                try:
                    from backend.email import start_delivery_worker
                    print("\n📧 Starting email delivery worker...")
                    await start_delivery_worker()
                    print("✓ Email delivery worker started (sending scheduled emails)")
                except Exception as e:
                    print(f"⚠️  Error starting delivery worker: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("ℹ️  Delivery worker disabled (ENABLE_DELIVERY_WORKER=false)")

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

        # Only stop in-process workers if we're NOT in Redis Queue mode
        redis_queue_enabled = getattr(config, 'redis_configured', False)

        if not redis_queue_enabled:
            # Stop background story worker
            try:
                from backend.jobs import stop_story_worker, close_queue
                print("🔄 Stopping background story worker...")
                stop_story_worker()
                await close_queue()
                print("✓ Background story worker stopped")
            except Exception as e:
                print(f"⚠️  Error stopping story worker: {e}")

            # Stop daily story scheduler
            try:
                from backend.jobs import stop_daily_scheduler
                print("📅 Stopping daily story scheduler...")
                stop_daily_scheduler()
                print("✓ Daily story scheduler stopped")
            except Exception as e:
                print(f"⚠️  Error stopping daily scheduler: {e}")

            # Stop email delivery worker
            try:
                from backend.email import stop_delivery_worker
                print("📧 Stopping email delivery worker...")
                stop_delivery_worker()
                print("✓ Email delivery worker stopped")
            except Exception as e:
                print(f"⚠️  Error stopping delivery worker: {e}")
        else:
            print("ℹ️  Redis Queue mode - no in-process workers to stop")

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
