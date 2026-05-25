from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):

    # ==========================================
    # Application
    # ==========================================

    app_name: str = "SENTINEL"
    debug: bool = True
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    # ==========================================
    # Database
    # ==========================================

    database_url: str = "sqlite+aiosqlite:///./sentinel.db"

    # ==========================================
    # Providers
    # ==========================================

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    PRIMARY_MODEL: str = "gemma4:31b-cloud"
    FALLBACK_MODEL: str = "gpt-oss:120b-cloud"
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    ollama_base_url: str = "http://localhost:11434"

    primary_model: str = "gpt-4o-mini"
    secondary_model: str = "gpt-4o-mini"
    tertiary_model: str = "llama3.1"

    # ==========================================
    # Retry / Failover
    # ==========================================

    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0

    request_timeout: float = 30.0

    # ==========================================
    # Circuit Breaker
    # ==========================================

    circuit_breaker_threshold: int = 3
    circuit_breaker_reset_timeout: int = 60

    # ==========================================
    # CORS
    # ==========================================

    cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    # ==========================================
    # Pydantic Settings Config
    # ==========================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()