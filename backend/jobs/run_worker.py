#!/usr/bin/env python3
"""
Standalone story worker process.

Run this as a separate process from the web server to avoid
gunicorn worker timeouts during long story generation.

Usage:
    python -m backend.jobs.run_worker
"""

import asyncio
import os
import signal
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.jobs.worker import StoryWorker


async def main():
    """Run the story worker as a standalone process."""
    print("=" * 60)
    print("Starting Standalone Story Worker")
    print("=" * 60)

    # Get database paths from environment or use defaults
    storage_path = os.getenv("STORAGE_PATH", ".")
    job_db_path = os.path.join(storage_path, "story_jobs.db") if storage_path != "." else "story_jobs.db"
    email_db_path = os.path.join(storage_path, "email_scheduler.db") if storage_path != "." else "email_scheduler.db"

    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL", "5"))

    print(f"  Job database: {job_db_path}")
    print(f"  Email database: {email_db_path}")
    print(f"  Poll interval: {poll_interval}s")
    print("=" * 60)

    worker = StoryWorker(
        job_db_path=job_db_path,
        email_db_path=email_db_path,
        poll_interval_seconds=poll_interval
    )

    # Handle shutdown signals gracefully
    shutdown_event = asyncio.Event()

    def handle_shutdown(signum, frame):
        print(f"\n  Received signal {signum}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        await worker.initialize()
        worker.start()

        print("\n  Worker running. Press Ctrl+C to stop.\n")

        # Keep running until shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        print(f"  Worker error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n  Shutting down worker...")
        worker.shutdown()
        if worker.job_db:
            await worker.job_db.close()
        if worker.email_db:
            await worker.email_db.close()
        print("  Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
