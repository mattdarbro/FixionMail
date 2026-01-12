#!/usr/bin/env python3
"""
FixionMail Service Entrypoint

This script determines which process to run based on the SERVICE_TYPE
environment variable. Set SERVICE_TYPE in each Railway service's settings.

SERVICE_TYPE values:
  - web (default): Run the FastAPI web server via gunicorn
  - worker: Run the RQ story/email worker
  - scheduler: Run the daily story scheduler
  - delivery: Run the email delivery scheduler
"""

import os
import sys
import subprocess

SERVICE_TYPE = os.environ.get("SERVICE_TYPE", "web")
PORT = os.environ.get("PORT", "8080")

print("=" * 50)
print(f"FixionMail Service: {SERVICE_TYPE}")
print("=" * 50)

if SERVICE_TYPE == "web":
    print("Starting web server (gunicorn)...")
    cmd = [
        "gunicorn", "backend.api.main:app",
        "--workers", "2",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--bind", f"0.0.0.0:{PORT}",
        "--timeout", "900",
        "--graceful-timeout", "120"
    ]
elif SERVICE_TYPE == "worker":
    print("Starting RQ worker (stories + emails queues)...")
    cmd = ["python", "-m", "backend.queue.run_worker", "--queues", "stories", "emails"]
elif SERVICE_TYPE == "scheduler":
    print("Starting daily story scheduler...")
    cmd = ["python", "-m", "backend.queue.run_scheduler"]
elif SERVICE_TYPE == "delivery":
    print("Starting email delivery scheduler...")
    cmd = ["python", "-m", "backend.queue.run_delivery"]
else:
    print(f"ERROR: Unknown SERVICE_TYPE: {SERVICE_TYPE}")
    print("Valid values: web, worker, scheduler, delivery")
    sys.exit(1)

print(f"Running: {' '.join(cmd)}")
print("=" * 50)

# Replace this process with the actual command
os.execvp(cmd[0], cmd)
