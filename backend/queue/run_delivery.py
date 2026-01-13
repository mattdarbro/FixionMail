#!/usr/bin/env python3
"""
Email Delivery Scheduler for FixionMail (Redis Queue version).

This script checks for due email deliveries and enqueues them to Redis
for processing by the email worker.

Usage:
    python -m backend.queue.run_delivery
"""

import asyncio
import sys
import os
import signal
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import config
from backend.utils.logging import job_logger as logger


class DeliveryQueueScheduler:
    """
    Scheduler that checks for due email deliveries and enqueues them to Redis.

    Polls the scheduled_deliveries table every minute and enqueues
    any due deliveries to the Redis email queue.
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self.scheduler = AsyncIOScheduler()
        self._is_checking = False
        self._running = False

    async def start(self):
        """Start the delivery scheduler."""
        if not config.REDIS_URL:
            logger.error("REDIS_URL not configured - delivery scheduler cannot start")
            return

        # Add job to check deliveries periodically
        self.scheduler.add_job(
            self._check_and_enqueue_deliveries,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id="delivery_check",
            name="Check for due email deliveries",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        self._running = True
        logger.info(
            "Delivery Queue Scheduler started",
            check_interval=self.check_interval
        )

    async def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("Delivery scheduler stopped")

    async def _check_and_enqueue_deliveries(self):
        """Check for due deliveries and enqueue them to Redis."""
        if self._is_checking:
            return

        self._is_checking = True

        try:
            from backend.database.deliveries import DeliveryService
            from backend.queue.tasks import enqueue_email_delivery

            delivery_service = DeliveryService()

            # Get deliveries that are due
            due_deliveries = await delivery_service.get_due_deliveries(limit=50)

            if not due_deliveries:
                return

            enqueued_count = 0

            for delivery in due_deliveries:
                delivery_id = delivery["id"]
                marked_sending = False

                try:
                    # Mark as sending first to prevent duplicate processing
                    await delivery_service.mark_sending(delivery_id)
                    marked_sending = True

                    # Enqueue to Redis
                    rq_job = enqueue_email_delivery(delivery_id)

                    logger.info(
                        f"Enqueued email delivery to Redis",
                        delivery_id=delivery_id,
                        rq_job_id=rq_job.id,
                        email=delivery.get("user_email")
                    )
                    enqueued_count += 1

                except Exception as delivery_error:
                    logger.error(
                        f"Error enqueuing delivery: {delivery_error}",
                        delivery_id=delivery_id,
                        error=str(delivery_error)
                    )
                    # If we marked as sending but failed to enqueue, revert to pending
                    # so it can be retried on the next check
                    if marked_sending:
                        try:
                            await delivery_service.reset_to_pending(delivery_id)
                            logger.info(f"Reset delivery to pending after enqueue failure", delivery_id=delivery_id)
                        except Exception as reset_error:
                            logger.error(f"Failed to reset delivery status: {reset_error}", delivery_id=delivery_id)

            if enqueued_count > 0:
                logger.info(f"Enqueued {enqueued_count} email delivery job(s)")

        except Exception as e:
            logger.error(f"Delivery check error: {e}", error=str(e))
        finally:
            self._is_checking = False


async def main():
    """Run the delivery scheduler."""
    print("=" * 50)
    print("FixionMail Email Delivery Scheduler (Redis Queue)")
    print("=" * 50)

    if not config.REDIS_URL:
        print("❌ ERROR: REDIS_URL environment variable is required")
        sys.exit(1)

    scheduler = DeliveryQueueScheduler()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        print("\n👋 Shutting down delivery scheduler...")
        asyncio.create_task(scheduler.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    await scheduler.start()

    print("✅ Delivery scheduler running. Press Ctrl+C to stop.")

    # Keep running
    try:
        while scheduler._running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

    print("Delivery scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
