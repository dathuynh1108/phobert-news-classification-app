from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VNN ML Backend"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    ai_service_host: str = "127.0.0.1"
    ai_service_port: int = 50051
    grpc_timeout_seconds: float = 6.0
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "vnn_ml"
    db_user: str = "vnn"
    db_password: str = "vnn"
    db_connect_timeout_seconds: int = 5
    db_schema: str = "public"

    model_config = SettingsConfigDict(
        env_prefix="VNN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        password = quote_plus(self.db_password)
        return f"postgresql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

