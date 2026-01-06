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

    # ===== Supabase Configuration =====
    SUPABASE_URL: str | None = Field(
        default=None,
        description="Supabase project URL"
    )

    SUPABASE_ANON_KEY: str | None = Field(
        default=None,
        description="Supabase anon/public key (for client-side auth)"
    )

    SUPABASE_SERVICE_KEY: str | None = Field(
        default=None,
        description="Supabase service role key (for server-side operations, bypasses RLS)"
    )

    SUPABASE_JWT_SECRET: str | None = Field(
        default=None,
        description="Supabase JWT secret for token verification"
    )

    # ===== Stripe Configuration =====
    STRIPE_SECRET_KEY: str | None = Field(
        default=None,
        description="Stripe secret key for server-side operations"
    )

    STRIPE_PUBLISHABLE_KEY: str | None = Field(
        default=None,
        description="Stripe publishable key for client-side"
    )

    STRIPE_WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Stripe webhook signing secret"
    )

    # Stripe Price IDs (set these after creating products in Stripe)
    STRIPE_PRICE_MONTHLY: str | None = Field(
        default=None,
        description="Stripe Price ID for monthly subscription ($9.99)"
    )

    STRIPE_PRICE_ANNUAL: str | None = Field(
        default=None,
        description="Stripe Price ID for annual subscription ($99)"
    )

    STRIPE_PRICE_CREDITS_5: str | None = Field(
        default=None,
        description="Stripe Price ID for 5 credit pack ($4.49)"
    )

    STRIPE_PRICE_CREDITS_10: str | None = Field(
        default=None,
        description="Stripe Price ID for 10 credit pack ($7.99)"
    )

    STRIPE_PRICE_CREDITS_20: str | None = Field(
        default=None,
        description="Stripe Price ID for 20 credit pack ($14.99)"
    )

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
        default="claude-sonnet-4-20250514",
        description="Claude model name for narrative generation (claude-sonnet-4-20250514 is the strongest model for complex prompts and long-form content)"
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
        default=16000,  # Sonnet 4 supports up to 16K output - give it plenty of room for 2500-word chapters + JSON
        ge=100,
        le=16000,
        description="Maximum tokens per LLM response (16000 = ~10K-12K words, ensures 2500-word chapters + JSON structure never get truncated)"
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

    APP_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for the application (used for auth redirects, emails, etc.)"
    )

    # ===== Security Settings =====
    API_KEYS: str | None = Field(
        default=None,
        description="Comma-separated list of valid API keys. If empty/None and DEV_MODE=True, auth is bypassed."
    )

    ALLOWED_ORIGINS: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins. Use '*' for all (dev only)."
    )

    RATE_LIMIT_PER_MINUTE: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Max API requests per minute per API key (0 = unlimited in dev mode)"
    )

    @property
    def api_keys_list(self) -> list[str]:
        """Get list of valid API keys."""
        if not self.API_KEYS:
            return []
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        """Get list of allowed CORS origins.

        Security: In production (DEV_MODE=false), '*' is not allowed.
        Falls back to APP_BASE_URL if no origins specified in production.
        """
        if self.ALLOWED_ORIGINS == "*":
            if self.DEV_MODE:
                return ["*"]
            else:
                # SECURITY: Don't allow '*' in production
                # Fall back to APP_BASE_URL as the only allowed origin
                import sys
                print(
                    "⚠️  WARNING: ALLOWED_ORIGINS='*' is not secure in production. "
                    f"Using APP_BASE_URL ({self.APP_BASE_URL}) instead. "
                    "Set ALLOWED_ORIGINS explicitly for production.",
                    file=sys.stderr
                )
                return [self.APP_BASE_URL]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def auth_required(self) -> bool:
        """Check if authentication is required (False in dev mode with no keys)."""
        return bool(self.api_keys_list) or not self.DEV_MODE

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
        """Check if audio generation is available (using OpenAI TTS)."""
        return (
            self.ENABLE_MEDIA_GENERATION
            and self.OPENAI_API_KEY is not None
        )

    @property
    def langsmith_enabled(self) -> bool:
        """Check if LangSmith tracing is properly configured."""
        return (
            self.LANGCHAIN_TRACING_V2
            and self.LANGCHAIN_API_KEY is not None
        )

    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return (
            self.SUPABASE_URL is not None
            and self.SUPABASE_ANON_KEY is not None
            and self.SUPABASE_SERVICE_KEY is not None
        )

    @property
    def stripe_configured(self) -> bool:
        """Check if Stripe is properly configured for subscriptions."""
        return (
            self.STRIPE_SECRET_KEY is not None
            and self.STRIPE_WEBHOOK_SECRET is not None
            and self.STRIPE_PRICE_MONTHLY is not None
        )

    @property
    def stripe_credit_packs_configured(self) -> bool:
        """Check if Stripe credit pack products are configured."""
        return (
            self.STRIPE_PRICE_CREDITS_5 is not None
            and self.STRIPE_PRICE_CREDITS_10 is not None
            and self.STRIPE_PRICE_CREDITS_20 is not None
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
    print(f"Supabase: {'✓' if config.supabase_configured else '✗'}")
    print(f"Stripe: {'✓' if config.stripe_configured else '✗'}")
    print(f"Stripe Credit Packs: {'✓' if config.stripe_credit_packs_configured else '✗'}")
