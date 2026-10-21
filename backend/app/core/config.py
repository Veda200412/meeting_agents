"""Core configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    LLM_PROVIDER: str = Field(default="gemini", description="LLM provider name")
    LLM_MODEL: str = Field(default="gemini-2.0-flash", description="Model identifier")
    GOOGLE_API_KEY: str = Field(default="", description="Google API key for Gemini")
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase public anon key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="", description="Server-only Supabase service role key"
    )

    MAX_REVIEW_CYCLES: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum review-correction cycles (in addition to first review)",
    )
    LLM_MAX_RETRIES: int = Field(default=2, ge=0, le=5)
    REQUEST_TIMEOUT_SECONDS: int = Field(default=60, ge=10, le=300)

    ENABLE_DEMO_FAULTS: bool = Field(
        default=False, description="Enable demo fault injection"
    )
    FRONTEND_ORIGIN: str = Field(default="http://localhost:5173")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_startup(self) -> list[str]:
        """Return list of configuration warnings/errors."""
        issues: list[str] = []
        if self.LLM_PROVIDER == "gemini" and not self.GOOGLE_API_KEY:
            issues.append(
                "GOOGLE_API_KEY is not set. LLM calls will fail. "
                "Set it in your .env file or environment."
            )
        return issues


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing)."""
    global _settings
    _settings = None
