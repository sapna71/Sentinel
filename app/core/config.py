from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field 

class Settings(BaseSettings):

    PROJECT_NAME: str = "SENTINEL"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = Field(default = "sqlite+aiosqlite:///./sentinel.db")

    OLLAMA_API_KEY: str = Field(default="")
    OLLAMA_HOST: str = Field(default="http://localhost:11434")

    PRIMARY_MODEL : str = "gemma4:31b-cloud"
    FALLBACK_MODEL : str = ""
    MAX_RETRIES : int = 3
    TIMEOUT : int = 30

    modelConfig = SettingsConfigDict(env_file=".env", env_file_encoding = "utf-8")

settings = Settings()