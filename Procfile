# ============================================================================
# FixionMail Process Configuration
# ============================================================================
#
# OPTION 1: Single-Process Mode (Current/Legacy)
# - Use 'web' process only
# - Workers run inside the FastAPI app via APScheduler
# - Simpler but doesn't scale
#
# OPTION 2: Multi-Process Mode with Redis Queue (Recommended for production)
# - Set ENABLE_REDIS_QUEUE=true and REDIS_URL=...
# - Use 'web' + 'worker' + 'scheduler' + 'delivery' processes
# - Better scalability and reliability
#
# ============================================================================

# Web API Server (always needed)
# - Handles HTTP requests, webhooks, API endpoints
# - In single-process mode, also runs background workers via APScheduler
web: gunicorn backend.api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 900 --graceful-timeout 120

# ============================================================================
# Redis Queue Processes (enable these when using ENABLE_REDIS_QUEUE=true)
# ============================================================================

# Story Generation Worker
# - Processes story generation jobs from Redis queue
# - Can scale horizontally (run multiple instances)
worker: python -m backend.queue.run_worker --queues stories emails

# Daily Story Scheduler
# - Checks which users need stories and enqueues jobs
# - Only run ONE instance
scheduler: python -m backend.queue.run_scheduler

# Email Delivery Scheduler
# - Checks for due deliveries and enqueues email jobs
# - Only run ONE instance
delivery: python -m backend.queue.run_delivery
