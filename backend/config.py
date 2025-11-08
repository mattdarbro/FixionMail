"""
Application configuration management using Pydantic Settings.

This module provides a type-safe, centralized configuration system
that loads from environment variables with sensible defaults.
"""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Application configuration loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    Settings are validated at startup using Pydantic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow both STORAGE_PATH and Storage_Path
        extra="ignore"
    )

    # ===== API Keys (Required) =====
    ANTHROPIC_API_KEY: str | None = Field(
        default=None,
        description="Anthropic API key for Claude (required for narrative generation)"
    )

    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for embeddings (required for RAG)"
    )

    # ===== Optional API Keys =====
    REPLICATE_API_TOKEN: str | None = Field(
        default=None,
        description="Replicate API token for image generation (optional for MVP)"
    )

    ELEVENLABS_API_KEY: str | None = Field(
        default=None,
        description="ElevenLabs API key for voice generation (optional for MVP)"
    )

    # ===== LangSmith Tracing (Optional but recommended) =====
    LANGCHAIN_TRACING_V2: bool = Field(
        default=False,
        description="Enable LangSmith tracing for debugging"
    )
    
    @field_validator('LANGCHAIN_TRACING_V2', mode='before')
    @classmethod
    def parse_bool_string(cls, v):
        """Parse boolean from string values (Railway env vars are strings)."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return False

    LANGCHAIN_PROJECT: str = Field(
        default="storyteller-app",
        description="LangSmith project name"
    )

    LANGCHAIN_API_KEY: str | None = Field(
        default=None,
        description="LangSmith API key for tracing"
    )

    # ===== Database Configuration =====
    DATABASE_URL: str = Field(
        default="sqlite:///./story.db",
        description="Database URL for session persistence"
    )

    CHECKPOINT_DB_PATH: str = Field(
        default="./story_checkpoints.db",
        description="Path to SQLite database for LangGraph checkpoints"
    )

    @property
    def checkpoint_db_path(self) -> str:
        """Get checkpoint DB path, using persistent storage if available (Railway)."""
        # If STORAGE_PATH is set (Railway volume mount), use it for checkpoints too
        storage_path = getattr(self, 'Storage_Path', None) or getattr(self, 'STORAGE_PATH', None)
        if storage_path:
            # Store checkpoints in the same persistent volume as ChromaDB
            return f"{storage_path}/story_checkpoints.db"
        return self.CHECKPOINT_DB_PATH

    # ===== Story Settings =====
    DEFAULT_WORLD: str = Field(
        default="west_haven",
        description="Default story world ID"
    )

    CHAPTER_TARGET_WORDS: int = Field(
        default=2500,
        ge=500,
        le=5000,
        description="Target word count per chapter (2500 = full audiobook experience)"
    )

    TOTAL_CHAPTERS: int = Field(
        default=30,
        ge=10,
        le=100,
        description="Total chapters in complete story arc"
    )

    CREDITS_PER_NEW_USER: int = Field(
        default=25,
        ge=0,
        description="Credits awarded to new users"
    )

    CREDITS_PER_CHOICE: int = Field(
        default=1,
        ge=0,
        description="Credits deducted per story choice"
    )

    # ===== RAG Configuration =====
    RAG_RETRIEVAL_K: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Number of documents to retrieve from vector store"
    )

    RAG_FETCH_K: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of documents to fetch before MMR filtering"
    )

    RAG_SEARCH_TYPE: Literal["mmr", "similarity"] = Field(
        default="mmr",
        description="Vector search algorithm (mmr for diversity, similarity for relevance)"
    )

    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="./chroma_db",
        description="Directory for ChromaDB persistence"
    )
    
    # Aliases for Railway compatibility (all uppercase variations take precedence if set)
    Storage_Path: str | None = Field(
        default=None,
        alias="STORAGE_PATH",  # Support both Storage_Path and STORAGE_PATH
        description="Alias for CHROMA_PERSIST_DIRECTORY (Railway volume mount path). If set, overrides CHROMA_PERSIST_DIRECTORY"
    )
    
    @property
    def chroma_persist_directory(self) -> str:
        """Get ChromaDB persistence directory, using Storage_Path/STORAGE_PATH if available."""
        # Check both possible attribute names (Storage_Path and STORAGE_PATH)
        storage_path = getattr(self, 'Storage_Path', None) or getattr(self, 'STORAGE_PATH', None)
        return storage_path if storage_path else self.CHROMA_PERSIST_DIRECTORY

    # ===== LLM Configuration =====
    MODEL_NAME: str = Field(
        default="claude-3-haiku-20240307",
        description="Claude model name for narrative generation (claude-3-haiku-20240307 for fast testing, claude-sonnet-4-20250514 for production)"
    )

    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for RAG"
    )

    TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for creativity control"
    )

    MAX_TOKENS: int = Field(
        default=8000,  # Increased from 4000 to ensure 2500-word chapters + full JSON structure don't get truncated
        ge=100,
        le=8000,
        description="Maximum tokens per LLM response (8000 = ~5000-6000 words, needed for 2500-word chapters + JSON)"
    )

    # ===== Feature Toggles (for phased development) =====
    ENABLE_STREAMING: bool = Field(
        default=True,
        description="Enable SSE streaming for narrative text"
    )

    STREAMING_WORDS_PER_SECOND: float = Field(
        default=7.5,
        ge=1.0,
        le=20.0,
        description="Words per second for narrative streaming (5-10 recommended for thoughtful pacing)"
    )

    ENABLE_MEDIA_GENERATION: bool = Field(
        default=True,
        description="Enable image/audio generation (requires API keys)"
    )

    ENABLE_CREDIT_SYSTEM: bool = Field(
        default=False,
        description="Enable credit tracking and limits (Phase 3 feature)"
    )

    # ===== Media Generation Settings =====
    IMAGE_MODEL: str = Field(
        default="stability-ai/sdxl:latest",
        description="Replicate model for image generation"
    )

    IMAGE_WIDTH: int = Field(
        default=1024,
        ge=256,
        le=2048,
        description="Generated image width"
    )

    IMAGE_HEIGHT: int = Field(
        default=1024,
        ge=256,
        le=2048,
        description="Generated image height"
    )

    ELEVENLABS_VOICE_ID: str = Field(
        default="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
        description="Default ElevenLabs voice ID"
    )

    # ===== Application Settings =====
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment mode: development or production"
    )

    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode (auto-set to False in production)"
    )

    DEV_MODE: bool = Field(
        default=True,
        description="Enable dev mode: synchronous generation with frontend for testing (disable for async email mode)"
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    API_HOST: str = Field(
        default="0.0.0.0",
        description="API server host"
    )

    API_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="API server port"
    )

    # ===== Computed Properties =====

    @property
    def can_generate_images(self) -> bool:
        """Check if image generation is available."""
        return (
            self.ENABLE_MEDIA_GENERATION
            and self.REPLICATE_API_TOKEN is not None
        )

    @property
    def can_generate_audio(self) -> bool:
        """Check if audio generation is available."""
        return (
            self.ENABLE_MEDIA_GENERATION
            and self.ELEVENLABS_API_KEY is not None
        )

    @property
    def langsmith_enabled(self) -> bool:
        """Check if LangSmith tracing is properly configured."""
        return (
            self.LANGCHAIN_TRACING_V2
            and self.LANGCHAIN_API_KEY is not None
        )


# Global configuration instance
# Import this in other modules: from backend.config import config
config = AppConfig()

# Disable LangSmith tracing if not properly configured
# This prevents 401 errors when LANGCHAIN_API_KEY is missing
if config.LANGCHAIN_TRACING_V2 and not config.LANGCHAIN_API_KEY:
    print("⚠️  LangSmith tracing is enabled but LANGCHAIN_API_KEY is missing. Disabling tracing.")
    import os
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    config.LANGCHAIN_TRACING_V2 = False


# Validation on startup
if __name__ == "__main__":
    print("Configuration loaded successfully!")
    print(f"Model: {config.MODEL_NAME}")
    print(f"Default World: {config.DEFAULT_WORLD}")
    print(f"RAG: {config.RAG_SEARCH_TYPE} (k={config.RAG_RETRIEVAL_K})")
    print(f"Image Generation: {'✓' if config.can_generate_images else '✗'}")
    print(f"Audio Generation: {'✓' if config.can_generate_audio else '✗'}")
    print(f"LangSmith Tracing: {'✓' if config.langsmith_enabled else '✗'}")
