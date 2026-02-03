"""
RQ Task Definitions for FixionMail.

These are the actual functions that run in the worker processes.
They are enqueued by the scheduler and executed asynchronously.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from rq import get_current_job, Retry
from rq.job import Job

from .connection import get_story_queue, get_email_queue, QUEUE_STORIES, QUEUE_EMAILS


# =============================================================================
# STORY GENERATION TASK
# =============================================================================

def generate_story_task(
    job_id: str,
    story_bible: Dict[str, Any],
    user_email: str,
    settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    RQ task for generating a story.

    This runs in a separate worker process and handles the full
    story generation pipeline.

    Args:
        job_id: Unique job identifier
        story_bible: The story configuration
        user_email: User's email for delivery
        settings: Generation settings (models, tier, etc.)

    Returns:
        Dict with success status and story/error details
    """
    # Run async code in sync context (RQ workers are sync)
    return asyncio.run(_generate_story_async(job_id, story_bible, user_email, settings or {}))


async def _generate_story_async(
    job_id: str,
    story_bible: Dict[str, Any],
    user_email: str,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Async implementation of story generation."""
    from backend.database.jobs import JobQueueService, JobStatus
    from backend.utils.logging import job_logger as logger

    job_service = JobQueueService()
    start_time = time.time()

    try:
        # Mark as running
        await job_service.update_status(
            job_id,
            JobStatus.RUNNING,
            current_step="starting",
            progress_percent=0
        )

        logger.info(f"RQ Worker: Processing story job", job_id=job_id, email=user_email)

        # Get model settings
        writer_model = settings.get("writer_model", "sonnet")
        structure_model = settings.get("structure_model", "sonnet")
        editor_model = settings.get("editor_model", "opus")
        user_tier = settings.get("user_tier", "free")
        dev_mode = settings.get("dev_mode", False)
        tts_provider = settings.get("tts_provider", "openai")
        tts_voice = settings.get("tts_voice")
        use_structure_agent = settings.get("use_structure_agent", True)

        # Delivery preferences
        delivery_time = settings.get("delivery_time", "08:00")
        user_timezone = settings.get("timezone", "UTC")
        immediate_delivery = settings.get("immediate_delivery", False)

        from backend.storyteller.standalone_generation import generate_standalone_story

        # Update progress: Structure phase
        await job_service.update_status(
            job_id,
            JobStatus.RUNNING,
            current_step="structure",
            progress_percent=10
        )

        # Run the full generation pipeline
        result = await generate_standalone_story(
            story_bible=story_bible,
            user_tier=user_tier,
            dev_mode=dev_mode,
            tts_provider=tts_provider,
            tts_voice=tts_voice,
            writer_model=writer_model,
            structure_model=structure_model,
            editor_model=editor_model,
            use_structure_agent=use_structure_agent
        )

        if not result.get("success"):
            raise Exception(result.get("error", "Unknown generation error"))

        story = result["story"]
        updated_bible = result.get("updated_bible", story_bible)

        # Update progress: Saving to database
        await job_service.update_status(
            job_id,
            JobStatus.RUNNING,
            current_step="saving",
            progress_percent=85
        )

        # Save story and schedule delivery
        story_id = None
        delivery_scheduled = False

        from backend.database.stories import StoryService
        from backend.database.users import UserService
        from backend.database.credits import CreditService
        from backend.database.deliveries import DeliveryService
        from backend.storyteller.bible_enhancement import update_story_history
        from backend.config import config

        if config.supabase_configured:
            user_service = UserService()
            user = await user_service.get_by_email(user_email)

            if user:
                # Update story history in the bible
                updated_bible = update_story_history(
                    updated_bible,
                    story["title"],
                    result.get("metadata", {}).get("summary", ""),
                    result.get("metadata", {}).get("plot_type", "")
                )

                # Save the story
                story_service = StoryService()
                story_record = await story_service.create(
                    user_id=user["id"],
                    title=story["title"],
                    narrative=story["narrative"],
                    genre=story.get("genre", "fiction"),
                    story_bible=updated_bible,
                    model_used=writer_model,
                    word_count=story.get("word_count", 0),
                    audio_url=story.get("audio_url"),
                    image_url=story.get("cover_image_url"),
                )
                story_id = story_record["id"]

                # Update user's story bible with new history/names
                await user_service.update_story_bible(user["id"], updated_bible)

                # Deduct credits if applicable
                if config.ENABLE_CREDIT_SYSTEM and user_tier != "free":
                    try:
                        credit_service = CreditService()
                        await credit_service.deduct_for_story(
                            user_id=user["id"],
                            story_id=story_id,
                            is_retell=False
                        )
                    except Exception as credit_error:
                        logger.error(f"Failed to deduct credits: {credit_error}")

                # Schedule delivery
                await job_service.update_status(
                    job_id,
                    JobStatus.RUNNING,
                    current_step="scheduling_delivery",
                    progress_percent=95
                )

                # Calculate delivery time
                if immediate_delivery:
                    deliver_at = datetime.now(timezone.utc)
                else:
                    deliver_at = _calculate_delivery_time(delivery_time, user_timezone)

                delivery_service = DeliveryService()
                await delivery_service.schedule_delivery(
                    story_id=story_id,
                    user_id=user["id"],
                    user_email=user_email,
                    deliver_at=deliver_at,
                    timezone_str=user_timezone
                )
                delivery_scheduled = True

                # Update last_story_at for daily stories
                is_daily = settings.get("is_daily", False)
                if is_daily:
                    await user_service.record_story_delivery(user["id"])

                logger.info(
                    f"Story saved and delivery scheduled",
                    story_id=story_id,
                    deliver_at=deliver_at.isoformat()
                )

        # Calculate total time
        generation_time = time.time() - start_time

        # Mark completed
        await job_service.mark_completed(
            job_id,
            result={
                "story": story,
                "story_id": story_id,
                "metadata": result.get("metadata", {}),
                "delivery_scheduled": delivery_scheduled
            },
            generation_time=generation_time,
            story_id=story_id
        )

        logger.info(
            f"Job completed",
            job_id=job_id,
            title=story['title'],
            word_count=story['word_count'],
            generation_time=f"{generation_time:.1f}s"
        )

        return {
            "success": True,
            "story_id": story_id,
            "title": story["title"],
            "delivery_scheduled": delivery_scheduled,
            "generation_time": generation_time
        }

    except Exception as e:
        generation_time = time.time() - start_time
        error_msg = str(e)

        logger.error(f"Job failed: {error_msg}", job_id=job_id, error=error_msg)

        # Mark failed with retry
        await job_service.mark_failed(
            job_id,
            error_message=error_msg,
            should_retry=True  # RQ handles retries, but we track in our DB too
        )

        return {
            "success": False,
            "error": error_msg,
            "generation_time": generation_time
        }


def _calculate_delivery_time(delivery_time: str, user_timezone: str) -> datetime:
    """Calculate the UTC datetime for delivery based on user preferences."""
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        tz = ZoneInfo("UTC")

    # Parse delivery time (HH:MM format)
    try:
        hour, minute = map(int, delivery_time.split(":"))
    except Exception:
        hour, minute = 8, 0  # Default to 8 AM

    # Get current time in user's timezone
    user_now = datetime.now(tz)

    # Create delivery datetime for today
    delivery_datetime = user_now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    # If the time has passed today, schedule for tomorrow
    if delivery_datetime <= user_now:
        delivery_datetime += timedelta(days=1)

    # Convert to UTC
    return delivery_datetime.astimezone(timezone.utc)


# =============================================================================
# EMAIL DELIVERY TASK
# =============================================================================

def send_email_task(delivery_id: str) -> Dict[str, Any]:
    """
    RQ task for sending a single email delivery.

    Args:
        delivery_id: ID of the scheduled_delivery record

    Returns:
        Dict with success status and details
    """
    return asyncio.run(_send_email_async(delivery_id))


async def _send_email_async(delivery_id: str) -> Dict[str, Any]:
    """Async implementation of email sending."""
    import os
    import resend
    from backend.database.deliveries import DeliveryService
    from backend.email.templates import render_story_email
    from backend.utils.logging import job_logger as logger

    delivery_service = DeliveryService()
    email_sent = False  # Track if email was successfully sent

    try:
        # Get delivery with story details
        delivery = await delivery_service.get_delivery_by_id(delivery_id)
        if not delivery:
            return {"success": False, "error": "Delivery not found"}

        # Check if already sent (prevents duplicate sends on retry)
        if delivery.get("status") == "sent":
            logger.info(f"Delivery already sent, skipping", delivery_id=delivery_id)
            return {"success": True, "already_sent": True}

        story = delivery.get("story")
        if not story:
            return {"success": False, "error": "Story not found for delivery"}

        # Atomically claim this delivery (prevents duplicate sends)
        # mark_sending only succeeds if status is currently 'pending'
        claimed = await delivery_service.mark_sending(delivery_id)
        if not claimed:
            logger.info(f"Delivery already claimed by another worker, skipping", delivery_id=delivery_id)
            return {"success": True, "already_claimed": True}

        # Render email HTML
        html_content = render_story_email(
            title=story["title"],
            narrative=story.get("narrative", ""),
            cover_image_url=story.get("image_url"),
            audio_url=story.get("audio_url"),
            genre=story.get("genre", "fiction"),
            word_count=story.get("word_count", 0)
        )

        # Send via Resend
        resend.api_key = os.environ.get("RESEND_API_KEY")

        params = {
            "from": os.environ.get("EMAIL_FROM", "FixionMail <stories@fixionmail.com>"),
            "to": [delivery["user_email"]],
            "subject": f"Your Story: {story['title']}",
            "html": html_content,
        }

        response = resend.Emails.send(params)
        resend_id = response.get("id")
        email_sent = True  # Email was successfully sent

        # Try to mark as sent - if this fails, we should NOT retry sending
        try:
            await delivery_service.mark_sent(
                delivery_id,
                resend_email_id=resend_id
            )
        except Exception as mark_error:
            # Email was sent but we couldn't update the database
            # Log the error but return success to prevent duplicate emails
            logger.error(
                f"Email sent but mark_sent failed - DO NOT RETRY",
                delivery_id=delivery_id,
                resend_id=resend_id,
                error=str(mark_error)
            )
            # Return success since email was sent - just couldn't update DB
            return {
                "success": True,
                "resend_id": resend_id,
                "email": delivery["user_email"],
                "warning": f"Email sent but database update failed: {mark_error}"
            }

        logger.info(
            f"Email sent successfully",
            delivery_id=delivery_id,
            email=delivery["user_email"],
            story_title=story["title"]
        )

        return {
            "success": True,
            "resend_id": resend_id,
            "email": delivery["user_email"]
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Email send failed: {error_msg}", delivery_id=delivery_id)

        # Only retry if email was NOT sent
        # If email was sent but something else failed, don't retry to prevent duplicates
        should_retry = not email_sent

        try:
            await delivery_service.mark_failed(
                delivery_id,
                error_message=error_msg,
                should_retry=should_retry
            )
        except Exception as mark_error:
            logger.error(f"Failed to mark delivery as failed: {mark_error}", delivery_id=delivery_id)

        return {
            "success": False,
            "error": error_msg,
            "email_was_sent": email_sent
        }


# =============================================================================
# QUEUE HELPERS
# =============================================================================

def enqueue_story_job(
    job_id: str,
    story_bible: Dict[str, Any],
    user_email: str,
    settings: Optional[Dict[str, Any]] = None
) -> Job:
    """
    Enqueue a story generation job to the Redis queue.

    Args:
        job_id: Unique job identifier
        story_bible: Story configuration
        user_email: User's email
        settings: Optional generation settings

    Returns:
        RQ Job instance
    """
    queue = get_story_queue()

    return queue.enqueue(
        generate_story_task,
        job_id,
        story_bible,
        user_email,
        settings,
        job_id=f"story_{job_id}",  # RQ job ID for tracking
        job_timeout="15m",  # Story generation can take a while
        result_ttl=86400,  # Keep results for 24 hours
        failure_ttl=604800,  # Keep failed jobs for 7 days
        retry=Retry(max=3),  # Retry up to 3 times on failure
    )


def enqueue_email_delivery(delivery_id: str) -> Job:
    """
    Enqueue an email delivery job to the Redis queue.

    Args:
        delivery_id: ID of the scheduled_delivery record

    Returns:
        RQ Job instance
    """
    queue = get_email_queue()

    return queue.enqueue(
        send_email_task,
        delivery_id,
        job_id=f"email_{delivery_id}",
        job_timeout="2m",  # Email should be quick
        result_ttl=3600,  # Keep results for 1 hour
        failure_ttl=86400,  # Keep failed jobs for 24 hours
        retry=Retry(max=3),
    )
