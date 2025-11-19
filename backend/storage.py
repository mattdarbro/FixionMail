"""
Media storage abstraction layer.

Supports:
- Local filesystem (development)
- Supabase Storage (production)

Environment variables:
- ENVIRONMENT: "development" or "production"
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Your Supabase service role key (for uploads)
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StorageBackend:
    """Abstract base for storage backends."""

    def upload_audio(self, file_path: str, filename: str) -> str:
        """Upload audio file and return public URL."""
        raise NotImplementedError

    def upload_image(self, file_path: str, filename: str) -> str:
        """Upload image file and return public URL."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage for development."""

    def __init__(self):
        self.audio_dir = Path("./generated_audio")
        self.image_dir = Path("./generated_images")

        # Ensure directories exist
        self.audio_dir.mkdir(exist_ok=True)
        self.image_dir.mkdir(exist_ok=True)

        logger.info("Using LOCAL storage backend")

    def upload_audio(self, file_path: str, filename: str) -> str:
        """
        For local storage, files are already in the right place.
        Just return the URL path.
        """
        # File should already be at file_path (generated_audio/filename)
        # Just return the URL
        return f"/audio/{filename}"

    def upload_image(self, file_path: str, filename: str) -> str:
        """
        For local storage, files are already in the right place.
        Just return the URL path.
        """
        # File should already be at file_path (generated_images/filename)
        # Just return the URL
        return f"/images/{filename}"


class SupabaseStorage(StorageBackend):
    """Supabase Storage backend for production."""

    def __init__(self, supabase_url: str, supabase_key: str):
        try:
            from supabase import create_client
            self.client = create_client(supabase_url, supabase_key)
            self.supabase_url = supabase_url
            logger.info("Using SUPABASE storage backend")
        except ImportError:
            raise ImportError(
                "supabase-py is required for Supabase storage. "
                "Install with: pip install supabase"
            )

    def upload_audio(self, file_path: str, filename: str) -> str:
        """Upload audio file to Supabase Storage."""
        try:
            # Read the file
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Upload to Supabase Storage (audio bucket)
            self.client.storage.from_("audio").upload(
                filename,
                file_data,
                file_options={"content-type": "audio/mpeg"}
            )

            # Return public URL
            public_url = f"{self.supabase_url}/storage/v1/object/public/audio/{filename}"
            logger.info(f"Uploaded audio to Supabase: {filename}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload audio to Supabase: {e}")
            # Fallback: return local URL (file still exists locally)
            logger.warning(f"Falling back to local URL for {filename}")
            return f"/audio/{filename}"

    def upload_image(self, file_path: str, filename: str) -> str:
        """Upload image file to Supabase Storage."""
        try:
            # Read the file
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Determine content type from extension
            ext = Path(filename).suffix.lower()
            content_type_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".gif": "image/gif"
            }
            content_type = content_type_map.get(ext, "image/png")

            # Upload to Supabase Storage (images bucket)
            self.client.storage.from_("images").upload(
                filename,
                file_data,
                file_options={"content-type": content_type}
            )

            # Return public URL
            public_url = f"{self.supabase_url}/storage/v1/object/public/images/{filename}"
            logger.info(f"Uploaded image to Supabase: {filename}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload image to Supabase: {e}")
            # Fallback: return local URL (file still exists locally)
            logger.warning(f"Falling back to local URL for {filename}")
            return f"/images/{filename}"


# Global storage instance
_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Get the configured storage backend (singleton)."""
    global _storage

    if _storage is None:
        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "production":
            # Use Supabase Storage in production
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                logger.warning(
                    "SUPABASE_URL or SUPABASE_SERVICE_KEY not set. "
                    "Falling back to local storage."
                )
                _storage = LocalStorage()
            else:
                try:
                    _storage = SupabaseStorage(supabase_url, supabase_key)
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase storage: {e}")
                    logger.warning("Falling back to local storage")
                    _storage = LocalStorage()
        else:
            # Use local storage in development
            _storage = LocalStorage()

    return _storage


# Convenience functions
def upload_audio(file_path: str, filename: str) -> str:
    """Upload audio file and return public URL."""
    return get_storage().upload_audio(file_path, filename)


def upload_image(file_path: str, filename: str) -> str:
    """Upload image file and return public URL."""
    return get_storage().upload_image(file_path, filename)
