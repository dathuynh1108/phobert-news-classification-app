from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 50051
    workers: int = 8
    active_artifact_dir: Path = Path("../dataset/artifacts/active")
    model_name: str = "vinai/phobert-base-v2"
    auto_approve_threshold: float = 0.75
    review_threshold: float = 0.68

    model_config = SettingsConfigDict(
        env_prefix="VNN_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

