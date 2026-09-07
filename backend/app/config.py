"""Watcha backend application configuration."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- App ---
    app_name: str = "Watcha"
    debug: bool = False
    cors_origins: str = "http://localhost:5173"

    # --- Supabase ---
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous/public key")
    supabase_service_role_key: str = Field(
        ..., description="Supabase service role key (server-side only)"
    )

    # --- OpenRouter ---
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash",
        description="Default OpenRouter model for AI analysis",
    )

    # --- Telegram ---
    telegram_bot_token: str = Field(..., description="Telegram Bot token from BotFather")

    # --- Data Sources ---
    finnhub_api_key: str = Field(..., description="Finnhub API key")
    marketaux_api_key: str = Field(..., description="Marketaux API key")

    # --- JWT ---
    jwt_secret: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing (fallback if not using Supabase Auth)",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24  # 24 hours

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
