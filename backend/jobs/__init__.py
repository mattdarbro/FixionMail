"""
Story job queue system for background generation.

Components:
- JobQueueService: Supabase-backed job storage
- StoryJobQueue: High-level queue interface
- StoryWorker: Background worker that processes jobs
- DailyStoryScheduler: Scheduler for daily story delivery

Usage:
    # In API endpoint - queue a job
    from backend.jobs import get_queue
    queue = await get_queue()
    job_id = await queue.enqueue(story_bible, email, settings)

    # In FastAPI startup - start worker and scheduler
    from backend.jobs import start_story_worker, start_daily_scheduler
    await start_story_worker()
    await start_daily_scheduler()

    # Check job status
    status = await queue.get_status(job_id)
"""

from backend.database.jobs import JobQueueService, JobStatus
from backend.jobs.queue import StoryJobQueue, get_queue, close_queue
from backend.jobs.worker import (
    StoryWorker,
    start_story_worker,
    stop_story_worker,
    get_worker
)
from backend.jobs.daily_scheduler import (
    DailyStoryScheduler,
    start_daily_scheduler,
    stop_daily_scheduler,
    get_daily_scheduler
)

__all__ = [
    # Database/Service
    "JobQueueService",
    "JobStatus",

    # Queue
    "StoryJobQueue",
    "get_queue",
    "close_queue",

    # Worker
    "StoryWorker",
    "start_story_worker",
    "stop_story_worker",
    "get_worker",

    # Daily Scheduler
    "DailyStoryScheduler",
    "start_daily_scheduler",
    "stop_daily_scheduler",
    "get_daily_scheduler",
]
