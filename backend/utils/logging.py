"""
Centralized logging system for FixionMail.

Provides an in-memory log buffer for the admin dashboard to display
recent logs, errors, and warnings without needing external log aggregation.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import deque
from enum import Enum
from threading import Lock


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry:
    """A single log entry."""

    def __init__(
        self,
        level: LogLevel,
        message: str,
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.timestamp = datetime.utcnow()
        self.level = level
        self.message = message
        self.source = source
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "metadata": self.metadata
        }


class LogBuffer:
    """
    Thread-safe in-memory circular buffer for log entries.

    Stores the most recent N log entries for display in the admin dashboard.
    """

    def __init__(self, max_size: int = 1000):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = Lock()
        self._error_count = 0
        self._warning_count = 0

    def add(self, entry: LogEntry):
        """Add a log entry to the buffer."""
        with self._lock:
            self._buffer.append(entry)
            if entry.level == LogLevel.ERROR or entry.level == LogLevel.CRITICAL:
                self._error_count += 1
            elif entry.level == LogLevel.WARNING:
                self._warning_count += 1

    def get_recent(
        self,
        limit: int = 100,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent log entries, optionally filtered."""
        with self._lock:
            entries = list(self._buffer)

        # Apply filters
        if level:
            entries = [e for e in entries if e.level == level]
        if source:
            entries = [e for e in entries if e.source == source]

        # Return most recent first, limited
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    def get_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors and critical entries."""
        with self._lock:
            entries = [
                e for e in self._buffer
                if e.level in (LogLevel.ERROR, LogLevel.CRITICAL)
            ]
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    def get_warnings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent warnings."""
        with self._lock:
            entries = [e for e in self._buffer if e.level == LogLevel.WARNING]
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    def get_stats(self) -> Dict[str, int]:
        """Get log statistics."""
        with self._lock:
            total = len(self._buffer)
            by_level = {}
            by_source = {}

            for entry in self._buffer:
                by_level[entry.level.value] = by_level.get(entry.level.value, 0) + 1
                by_source[entry.source] = by_source.get(entry.source, 0) + 1

        return {
            "total": total,
            "by_level": by_level,
            "by_source": by_source,
            "error_count": self._error_count,
            "warning_count": self._warning_count
        }

    def clear(self):
        """Clear all log entries."""
        with self._lock:
            self._buffer.clear()
            self._error_count = 0
            self._warning_count = 0


# Global log buffer instance
_log_buffer = LogBuffer()


def get_log_buffer() -> LogBuffer:
    """Get the global log buffer instance."""
    return _log_buffer


class AppLogger:
    """
    Application logger that logs to both Python logging and the in-memory buffer.
    """

    def __init__(self, source: str):
        self.source = source
        self._logger = logging.getLogger(source)

    def _log(
        self,
        level: LogLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Internal method to log to both destinations."""
        # Add to buffer
        entry = LogEntry(level, message, self.source, metadata)
        _log_buffer.add(entry)

        # Also log to Python logging
        log_level = getattr(logging, level.value.upper())
        extra_msg = f" | {metadata}" if metadata else ""
        self._logger.log(log_level, f"{message}{extra_msg}")

    def debug(self, message: str, **metadata):
        self._log(LogLevel.DEBUG, message, metadata if metadata else None)

    def info(self, message: str, **metadata):
        self._log(LogLevel.INFO, message, metadata if metadata else None)

    def warning(self, message: str, **metadata):
        self._log(LogLevel.WARNING, message, metadata if metadata else None)

    def error(self, message: str, **metadata):
        self._log(LogLevel.ERROR, message, metadata if metadata else None)

    def critical(self, message: str, **metadata):
        self._log(LogLevel.CRITICAL, message, metadata if metadata else None)


def get_logger(source: str) -> AppLogger:
    """Get an AppLogger for a specific source/module."""
    return AppLogger(source)


# Pre-configured loggers for common sources
story_logger = AppLogger("story_generation")
job_logger = AppLogger("job_queue")
email_logger = AppLogger("email")
auth_logger = AppLogger("auth")
api_logger = AppLogger("api")
