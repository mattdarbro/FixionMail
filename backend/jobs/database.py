"""
Database schema for story job queue.
Uses aiosqlite for async SQLite operations.
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class JobStatus(str, Enum):
    """Status values for story generation jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryJobDatabase:
    """Handles story job queue database operations"""

    def __init__(self, db_path: str = "story_jobs.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database and create tables if needed"""
        db_file = Path(self.db_path)
        db_dir = db_file.parent
        if db_dir and str(db_dir) != "." and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

        # Enable WAL mode and set timeout for better concurrent access
        self._conn = await aiosqlite.connect(self.db_path, timeout=30.0)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        await self._create_tables()

    async def _create_tables(self):
        """Create required tables"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS story_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',

                -- Input data (JSON)
                story_bible TEXT NOT NULL,
                user_email TEXT NOT NULL,
                settings TEXT,  -- JSON: writer_model, structure_model, editor_model, etc.

                -- Progress tracking
                current_step TEXT,  -- 'structure', 'writer', 'editor', 'image', 'audio', 'email'
                progress_percent INTEGER DEFAULT 0,

                -- Output data (JSON, populated on completion)
                result TEXT,
                error_message TEXT,

                -- Timestamps
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,

                -- Metadata
                generation_time_seconds REAL,
                retry_count INTEGER DEFAULT 0
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON story_jobs(status, created_at)
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id
            ON story_jobs(job_id)
        """)

        await self._conn.commit()

    async def create_job(
        self,
        job_id: str,
        story_bible: Dict[str, Any],
        user_email: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new story generation job.

        Returns the database row ID.
        """
        cursor = await self._conn.execute("""
            INSERT INTO story_jobs
            (job_id, story_bible, user_email, settings, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            job_id,
            json.dumps(story_bible),
            user_email,
            json.dumps(settings) if settings else None,
            datetime.utcnow().isoformat()
        ))
        await self._conn.commit()
        return cursor.lastrowid

    async def get_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending jobs ordered by creation time (FIFO)"""
        cursor = await self._conn.execute("""
            SELECT id, job_id, story_bible, user_email, settings, created_at, retry_count
            FROM story_jobs
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))

        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "job_id": row[1],
                "story_bible": json.loads(row[2]),
                "user_email": row[3],
                "settings": json.loads(row[4]) if row[4] else {},
                "created_at": row[5],
                "retry_count": row[6]
            }
            for row in rows
        ]

    async def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by its job_id"""
        cursor = await self._conn.execute("""
            SELECT id, job_id, status, story_bible, user_email, settings,
                   current_step, progress_percent, result, error_message,
                   created_at, started_at, completed_at, generation_time_seconds
            FROM story_jobs
            WHERE job_id = ?
        """, (job_id,))

        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "job_id": row[1],
            "status": row[2],
            "story_bible": json.loads(row[3]),
            "user_email": row[4],
            "settings": json.loads(row[5]) if row[5] else {},
            "current_step": row[6],
            "progress_percent": row[7],
            "result": json.loads(row[8]) if row[8] else None,
            "error_message": row[9],
            "created_at": row[10],
            "started_at": row[11],
            "completed_at": row[12],
            "generation_time_seconds": row[13]
        }

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        current_step: Optional[str] = None,
        progress_percent: Optional[int] = None
    ):
        """Update job status and progress"""
        updates = ["status = ?"]
        values = [status.value]

        if current_step is not None:
            updates.append("current_step = ?")
            values.append(current_step)

        if progress_percent is not None:
            updates.append("progress_percent = ?")
            values.append(progress_percent)

        if status == JobStatus.RUNNING:
            updates.append("started_at = ?")
            values.append(datetime.utcnow().isoformat())

        values.append(job_id)

        await self._conn.execute(f"""
            UPDATE story_jobs
            SET {', '.join(updates)}
            WHERE job_id = ?
        """, values)
        await self._conn.commit()

    async def mark_completed(
        self,
        job_id: str,
        result: Dict[str, Any],
        generation_time: float
    ):
        """Mark a job as completed with its result"""
        await self._conn.execute("""
            UPDATE story_jobs
            SET status = 'completed',
                result = ?,
                completed_at = ?,
                generation_time_seconds = ?,
                progress_percent = 100,
                current_step = 'done'
            WHERE job_id = ?
        """, (
            json.dumps(result),
            datetime.utcnow().isoformat(),
            generation_time,
            job_id
        ))
        await self._conn.commit()

    async def mark_failed(
        self,
        job_id: str,
        error_message: str,
        should_retry: bool = False
    ):
        """Mark a job as failed"""
        if should_retry:
            # Increment retry count and reset to pending
            await self._conn.execute("""
                UPDATE story_jobs
                SET status = 'pending',
                    error_message = ?,
                    retry_count = retry_count + 1,
                    current_step = NULL,
                    progress_percent = 0
                WHERE job_id = ?
            """, (error_message, job_id))
        else:
            # Mark as permanently failed
            await self._conn.execute("""
                UPDATE story_jobs
                SET status = 'failed',
                    error_message = ?,
                    completed_at = ?
                WHERE job_id = ?
            """, (
                error_message,
                datetime.utcnow().isoformat(),
                job_id
            ))
        await self._conn.commit()

    async def get_recent_jobs(
        self,
        email: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent jobs, optionally filtered by email"""
        if email:
            cursor = await self._conn.execute("""
                SELECT job_id, status, current_step, progress_percent,
                       created_at, completed_at, generation_time_seconds
                FROM story_jobs
                WHERE user_email = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (email, limit))
        else:
            cursor = await self._conn.execute("""
                SELECT job_id, status, current_step, progress_percent,
                       created_at, completed_at, generation_time_seconds
                FROM story_jobs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        rows = await cursor.fetchall()
        return [
            {
                "job_id": row[0],
                "status": row[1],
                "current_step": row[2],
                "progress_percent": row[3],
                "created_at": row[4],
                "completed_at": row[5],
                "generation_time_seconds": row[6]
            }
            for row in rows
        ]

    async def get_completed_stories(
        self,
        email: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get completed stories with full content for the library.
        Returns stories with title, narrative, audio_url, image_url, etc.
        """
        if email:
            cursor = await self._conn.execute("""
                SELECT job_id, user_email, result, story_bible,
                       created_at, completed_at, generation_time_seconds
                FROM story_jobs
                WHERE status = 'completed'
                AND result IS NOT NULL
                AND user_email = ?
                ORDER BY completed_at DESC
                LIMIT ? OFFSET ?
            """, (email, limit, offset))
        else:
            cursor = await self._conn.execute("""
                SELECT job_id, user_email, result, story_bible,
                       created_at, completed_at, generation_time_seconds
                FROM story_jobs
                WHERE status = 'completed'
                AND result IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = await cursor.fetchall()
        stories = []

        for row in rows:
            result = json.loads(row[2]) if row[2] else {}
            story_data = result.get("story", {})
            bible = json.loads(row[3]) if row[3] else {}

            stories.append({
                "job_id": row[0],
                "user_email": row[1],
                "title": story_data.get("title", "Untitled"),
                "narrative": story_data.get("narrative", ""),
                "genre": story_data.get("genre") or bible.get("genre", "unknown"),
                "word_count": story_data.get("word_count", 0),
                "audio_url": story_data.get("audio_url"),
                "cover_image_url": story_data.get("cover_image_url"),
                "created_at": row[4],
                "completed_at": row[5],
                "generation_time_seconds": row[6],
                "metadata": result.get("metadata", {}),
                "email_sent": result.get("email_sent", False)
            })

        return stories

    async def get_story_count(self, email: Optional[str] = None) -> int:
        """Get total count of completed stories."""
        if email:
            cursor = await self._conn.execute("""
                SELECT COUNT(*) FROM story_jobs
                WHERE status = 'completed' AND result IS NOT NULL AND user_email = ?
            """, (email,))
        else:
            cursor = await self._conn.execute("""
                SELECT COUNT(*) FROM story_jobs
                WHERE status = 'completed' AND result IS NOT NULL
            """)

        row = await cursor.fetchone()
        return row[0] if row else 0

    async def cleanup_old_jobs(self, days: int = 30):
        """Remove completed/failed jobs older than specified days"""
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        await self._conn.execute("""
            DELETE FROM story_jobs
            WHERE status IN ('completed', 'failed')
            AND created_at < ?
        """, (cutoff,))
        await self._conn.commit()

    async def recover_stale_running_jobs(self, stale_minutes: int = 10) -> int:
        """
        Recover jobs stuck in 'running' status (e.g., after worker crash).

        Jobs running for longer than stale_minutes are reset to 'pending'
        so they can be re-processed.

        Returns the number of recovered jobs.
        """
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=stale_minutes)).isoformat()

        # Find and reset stale running jobs
        cursor = await self._conn.execute("""
            UPDATE story_jobs
            SET status = 'pending',
                current_step = NULL,
                progress_percent = 0,
                error_message = 'Recovered from stale running state (worker crash/timeout)'
            WHERE status = 'running'
            AND started_at < ?
            AND retry_count < 3
            RETURNING job_id
        """, (cutoff,))

        recovered = await cursor.fetchall()
        await self._conn.commit()

        return len(recovered)

    async def close(self):
        """Close database connection"""
        if self._conn:
            await self._conn.close()
