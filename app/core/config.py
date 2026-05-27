from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "SENTINEL"

    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel.db"

    OPENAI_API_KEY: str
    OPENROUTER_API_KEY: str

    PRIMARY_MODEL: str = "gpt-4o-mini"

    SECONDARY_MODEL: str = (
        "gpt-4o-mini"
    )

    FALLBACK_MODEL: str = "gpt-4o-mini"

    EMERGENCY_MODEL: str = "meta-llama/llama-3.1-8b-instruct"

    MAX_RETRIES: int = 2

    REQUEST_TIMEOUT: int = 30

    CIRCUIT_BREAKER_THRESHOLD: int = 3

    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 60

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()