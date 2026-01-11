#!/usr/bin/env python3
"""
RQ Worker Runner for FixionMail.

This script runs the RQ worker process that handles story generation
and email delivery jobs. Run this separately from the web server.

Usage:
    python -m backend.queue.run_worker                    # All queues
    python -m backend.queue.run_worker --queues stories   # Only stories
    python -m backend.queue.run_worker --queues emails    # Only emails
    python -m backend.queue.run_worker --burst            # Process and exit
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from rq import Worker, Queue
from rq.job import Job

from backend.queue.connection import (
    get_redis_connection,
    QUEUE_STORIES,
    QUEUE_EMAILS,
    QUEUE_DEFAULT
)
from backend.config import config


def main():
    parser = argparse.ArgumentParser(description="Run FixionMail RQ worker")
    parser.add_argument(
        "--queues",
        "-q",
        nargs="+",
        default=[QUEUE_STORIES, QUEUE_EMAILS],
        help=f"Queues to process (default: {QUEUE_STORIES} {QUEUE_EMAILS})"
    )
    parser.add_argument(
        "--burst",
        "-b",
        action="store_true",
        help="Run in burst mode (process all jobs and exit)"
    )
    parser.add_argument(
        "--name",
        "-n",
        default=None,
        help="Worker name (auto-generated if not specified)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Validate Redis configuration
    if not config.REDIS_URL:
        print("❌ ERROR: REDIS_URL environment variable is required")
        print("   Set up Upstash Redis or local Redis and configure REDIS_URL")
        sys.exit(1)

    try:
        # Get Redis connection
        conn = get_redis_connection()
        print(f"✅ Connected to Redis")

        # Create queues
        queues = [Queue(name, connection=conn) for name in args.queues]
        queue_names = ", ".join(args.queues)
        print(f"📋 Listening on queues: {queue_names}")

        # Create and run worker
        worker = Worker(
            queues,
            connection=conn,
            name=args.name,
        )

        print(f"🚀 Worker starting {'(burst mode)' if args.burst else ''}")
        print("   Press Ctrl+C to stop")
        print("-" * 50)

        # Run worker
        worker.work(
            burst=args.burst,
            logging_level="DEBUG" if args.verbose else "INFO",
            with_scheduler=True,  # Enable RQ scheduler for delayed jobs
        )

    except KeyboardInterrupt:
        print("\n👋 Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
