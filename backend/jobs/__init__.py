"""
Story job queue system for background generation.

Components:
- StoryJobDatabase: SQLite-backed job storage
- StoryJobQueue: High-level queue interface
- StoryWorker: Background worker that processes jobs

Usage:
    # In API endpoint - queue a job
    from backend.jobs import get_queue
    queue = await get_queue()
    job_id = await queue.enqueue(story_bible, email, settings)

    # In FastAPI startup - start worker
    from backend.jobs import start_story_worker, stop_story_worker
    await start_story_worker()

    # Check job status
    status = await queue.get_status(job_id)
"""

from backend.jobs.database import StoryJobDatabase, JobStatus
from backend.jobs.queue import StoryJobQueue, get_queue, close_queue
from backend.jobs.worker import (
    StoryWorker,
    start_story_worker,
    stop_story_worker,
    get_worker
)

__all__ = [
    # Database
    "StoryJobDatabase",
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
]
