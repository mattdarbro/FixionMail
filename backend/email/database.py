"""
Database schema for email scheduling.
Uses aiosqlite for async SQLite operations.
"""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional


class EmailDatabase:
    """Handles email-related database operations"""

    def __init__(self, db_path: str = "email_scheduler.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database and create tables if needed"""
        # Ensure database directory exists
        db_file = Path(self.db_path)
        db_dir = db_file.parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        await self._create_tables()

    async def _create_tables(self):
        """Create required tables"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                email TEXT NOT NULL,
                chapter INTEGER NOT NULL,
                audio_url TEXT,
                image_url TEXT,
                choices TEXT,  -- JSON string
                send_at TEXT NOT NULL,  -- ISO format datetime
                sent INTEGER DEFAULT 0,  -- 0=false, 1=true
                created_at TEXT NOT NULL,
                sent_at TEXT,
                error_message TEXT
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_send_at
            ON scheduled_emails(send_at, sent)
        """)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                session_id TEXT,
                world_id TEXT,
                created_at TEXT NOT NULL,
                last_active TEXT
            )
        """)

        await self._conn.commit()

    async def schedule_email(
        self,
        session_id: str,
        email: str,
        chapter: int,
        audio_url: str,
        image_url: Optional[str],
        choices: str,  # JSON string
        send_at: datetime
    ):
        """Schedule an email for future delivery"""
        await self._conn.execute("""
            INSERT INTO scheduled_emails
            (session_id, email, chapter, audio_url, image_url, choices, send_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            email,
            chapter,
            audio_url,
            image_url,
            choices,
            send_at.isoformat(),
            datetime.utcnow().isoformat()
        ))
        await self._conn.commit()

    async def get_due_emails(self, limit: int = 100):
        """Get all unsent emails that are due to be sent"""
        cursor = await self._conn.execute("""
            SELECT id, session_id, email, chapter, audio_url, image_url, choices
            FROM scheduled_emails
            WHERE send_at <= ? AND sent = 0
            ORDER BY send_at ASC
            LIMIT ?
        """, (datetime.utcnow().isoformat(), limit))

        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "session_id": row[1],
                "email": row[2],
                "chapter": row[3],
                "audio_url": row[4],
                "image_url": row[5],
                "choices": row[6],  # JSON string - parse when needed
            }
            for row in rows
        ]

    async def mark_sent(self, email_id: int, success: bool = True, error: Optional[str] = None):
        """Mark an email as sent (or failed)"""
        await self._conn.execute("""
            UPDATE scheduled_emails
            SET sent = ?, sent_at = ?, error_message = ?
            WHERE id = ?
        """, (
            1 if success else 0,
            datetime.utcnow().isoformat(),
            error,
            email_id
        ))
        await self._conn.commit()

    async def store_user(
        self,
        user_id: str,
        email: str,
        session_id: str,
        world_id: str
    ):
        """Store or update user information"""
        await self._conn.execute("""
            INSERT INTO users (user_id, email, session_id, world_id, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email = excluded.email,
                session_id = excluded.session_id,
                world_id = excluded.world_id,
                last_active = excluded.last_active
        """, (
            user_id,
            email,
            session_id,
            world_id,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        await self._conn.commit()

    async def get_user_by_session(self, session_id: str) -> Optional[dict]:
        """Get user by session ID"""
        cursor = await self._conn.execute("""
            SELECT user_id, email, world_id
            FROM users
            WHERE session_id = ?
        """, (session_id,))

        row = await cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "email": row[1],
                "world_id": row[2]
            }
        return None

    async def close(self):
        """Close database connection"""
        if self._conn:
            await self._conn.close()
