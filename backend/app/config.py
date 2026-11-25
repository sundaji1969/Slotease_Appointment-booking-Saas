from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables / .env (never hard-coded)."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MIN: int = 60
    JWT_ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:5173"
    APP_BASE_URL: str = "http://localhost:5173"
    RESEND_API_KEY: str | None = None
    RESEND_FROM: str = "SlotEase <onboarding@resend.dev>"
    RATE_LIMIT_ENABLED: bool = True
    BCRYPT_ROUNDS: int = 12

    # Booking assistant (optional). Without a key the assistant is hidden/disabled.
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Booking rules
    LEAD_TIME_MIN: int = 30
    MAX_DAYS_AHEAD: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        # Neon/Render hand out postgres:// URLs; normalise to the psycopg3 driver.
        url = self.DATABASE_URL
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
