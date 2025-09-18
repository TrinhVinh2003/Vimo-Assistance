import enum
from pathlib import Path
from tempfile import gettempdir

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    TITLE: str = "Fast API App"
    VERSION: str = "0.0.1"
    DESCRIPTION: str = ""
    PUBLIC_DOMAIN: str = ""
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    # quantity of workers for uvicorn
    WORKERS: int = 1
    # Enable uvicorn reloading
    RELOAD: bool = False
    # Current environment
    ENVIRONMENT: str = "dev"
    # Logging configuration
    LOG_LEVEL: LogLevel = LogLevel.INFO
    # Path to the directory with media
    MEDIA_DIR: str = "media"

    # LLMs key
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str

    # Database configuration
    PGVECTOR_SERVER: str = "localhost"
    PGVECTOR_PORT: int = 5432
    PGVECTOR_USER: str = "admin"
    PGVECTOR_PASSWORD: str = "admin"
    PGVECTOR_DB: str = "pgvector"
    PGVECTOR_ECHO: bool = True

    DB_VECTOR_SCHEMA: str = "vectordb"

    @computed_field  # type: ignore
    @property
    def base_db_url(self) -> PostgresDsn:
        """
        Get base database URL.

        :return: database URL.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.PGVECTOR_USER,
            password=self.PGVECTOR_PASSWORD,
            host=self.PGVECTOR_SERVER,
            port=self.PGVECTOR_PORT,
        ).unicode_string()

    @computed_field  # type: ignore
    @property
    def db_url(self) -> PostgresDsn:
        """
        Get database URL.

        :return: database URL.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.PGVECTOR_USER,
            password=self.PGVECTOR_PASSWORD,
            host=self.PGVECTOR_SERVER,
            port=self.PGVECTOR_PORT,
            path=f"{self.PGVECTOR_DB or ''}",
        ).unicode_string()

    @property
    def media_dir_static(self) -> Path:
        """
        Get path to the directory with media files.

        :return: path to the directory.
        """
        static_dir = Path(self.MEDIA_DIR)
        # create directory if not exists
        static_dir.mkdir(parents=True, exist_ok=True)
        return static_dir

    @property
    def media_base_url(self) -> str:
        """Get base URL for media files."""
        if self.PUBLIC_DOMAIN:
            return f"{self.PUBLIC_DOMAIN}/static/media"
        return f"{self.HOST}:{self.PORT}/static/media"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
