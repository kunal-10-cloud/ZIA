"""
Settings — All configuration lives here.
Never import from os.environ directly anywhere in the codebase.
Always import from here: from backend.config.settings import settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── LLM — OpenRouter ──────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    CLAUDE_SONNET_MODEL: str = "anthropic/claude-sonnet-4-6"
    CLAUDE_HAIKU_MODEL: str = "anthropic/claude-haiku-4-5-20251001"

    # ── Database ──────────────────────────────────────────────────────────────
    # Docker Compose fills these automatically in dev
    DATABASE_URL: str = "postgresql+asyncpg://zia:zia_dev_password@postgres:5432/zia_db"
    DATABASE_URL_SYNC: str = "postgresql://zia:zia_dev_password@postgres:5432/zia_db"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-change-in-production"

    # ── Token budget ──────────────────────────────────────────────────────────
    TOKEN_BUDGET_MAX: int = 10700
    TOKEN_BUDGET_WARN: int = 9000

    # ── Dev flags ─────────────────────────────────────────────────────────────
    LOG_ASSEMBLED_PROMPTS: bool = False
    MOCK_LLM_IN_TESTS: bool = False

    # ── Voice (Phase C) ───────────────────────────────────────────────────────
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_WS_URL: str = ""
    DEEPGRAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # ── WhatsApp (Phase E) ────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()