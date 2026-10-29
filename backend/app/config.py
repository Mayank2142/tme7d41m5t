"""Validate deployment configuration without exposing database credentials."""

from datetime import time
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEVELOPMENT_DATABASE_URL = "postgresql+psycopg://winddesk:winddesk_local@127.0.0.1:5432/winddesk"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GRID_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
        validate_default=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(DEVELOPMENT_DATABASE_URL)
    default_cutoff_local: time = time(9, 0)
    db_pool_size: int = Field(default=3, ge=1, le=10)
    db_max_overflow: int = Field(default=2, ge=0, le=10)
    frontend_dist: Path = Path("frontend/dist")
    build_sha: str = Field(default="local", min_length=1, max_length=64)
    api_rate_limit_enabled: bool = True
    api_rate_limit_per_minute: int = Field(default=120, ge=1, le=10_000)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            parsed = make_url(value.get_secret_value())
        except ArgumentError as exc:
            raise ValueError("Database URL must be a valid PostgreSQL connection URL") from exc
        if parsed.drivername != "postgresql+psycopg" or not parsed.database or not parsed.host:
            raise ValueError("Use a postgresql+psycopg URL with a host and database name")
        return value

    @field_validator("default_cutoff_local")
    @classmethod
    def validate_cutoff(cls, value: time) -> time:
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("Cutoff must be a local HH:MM value without seconds or an offset")
        return value

    @model_validator(mode="after")
    def validate_production_credentials(self) -> "Settings":
        if (
            self.environment == "production"
            and self.database_url.get_secret_value() == DEVELOPMENT_DATABASE_URL
        ):
            raise ValueError("Production requires an explicit GRID_DATABASE_URL")
        return self
