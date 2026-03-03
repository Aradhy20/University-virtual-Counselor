"""
Centralized application settings loaded from environment variables.
Uses Pydantic BaseSettings for validation and type safety.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # AI Providers
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: Optional[str] = None
    DEEPGRAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # Database
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./data/aditi.db"

    # Telephony
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # App Config
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    # Tracing
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_PROJECT: str = "tmu-counselor"
    LANGCHAIN_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
