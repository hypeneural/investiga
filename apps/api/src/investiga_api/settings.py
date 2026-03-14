"""Central settings using pydantic-settings.

Reads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "DEBUG"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── PostgreSQL ────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "investiga_tijucas"
    postgres_user: str = "investiga"
    postgres_password: str = "investiga_dev"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+psycopg_async://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── RabbitMQ ──────────────────────────────────────────
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "investiga"
    rabbitmq_password: str = "investiga_dev"

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}"
        )

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenRouter (LLM) ─────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Minha Receita ─────────────────────────────────────
    minha_receita_base_url: str = "https://minhareceita.org"

    # ── Sentry ────────────────────────────────────────────
    sentry_dsn: str = ""

    # ── Timeouts (seconds) ────────────────────────────────
    timeout_atende: int = 30
    timeout_minha_receita: int = 20
    timeout_openrouter: int = 120


settings = Settings()
