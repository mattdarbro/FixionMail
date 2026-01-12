#!/bin/bash
# ============================================================================
# FixionMail Entrypoint Script
# ============================================================================
# This script determines which process to run based on the SERVICE_TYPE
# environment variable. Set SERVICE_TYPE in each Railway service's settings.
#
# SERVICE_TYPE values:
#   - web (default): Run the FastAPI web server
#   - worker: Run the RQ story/email worker
#   - scheduler: Run the daily story scheduler
#   - delivery: Run the email delivery scheduler
# ============================================================================

set -e

SERVICE_TYPE="${SERVICE_TYPE:-web}"

echo "=============================================="
echo "FixionMail Service: $SERVICE_TYPE"
echo "=============================================="

case "$SERVICE_TYPE" in
    web)
        echo "Starting web server (gunicorn)..."
        exec gunicorn backend.api.main:app \
            --workers 2 \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind 0.0.0.0:${PORT:-8080} \
            --timeout 900 \
            --graceful-timeout 120
        ;;
    worker)
        echo "Starting RQ worker (stories + emails queues)..."
        exec python -m backend.queue.run_worker --queues stories emails
        ;;
    scheduler)
        echo "Starting daily story scheduler..."
        exec python -m backend.queue.run_scheduler
        ;;
    delivery)
        echo "Starting email delivery scheduler..."
        exec python -m backend.queue.run_delivery
        ;;
    *)
        echo "ERROR: Unknown SERVICE_TYPE: $SERVICE_TYPE"
        echo "Valid values: web, worker, scheduler, delivery"
        exit 1
        ;;
esac
