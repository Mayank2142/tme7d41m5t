"""Validate deployment configuration without exposing database credentials."""

import os
import re
from datetime import time
from ipaddress import ip_network
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
    api_max_inflight: int = Field(default=64, ge=1, le=128)
    response_cache_mb: int = Field(default=32, ge=1, le=128)
    source_cache_mb: int = Field(default=32, ge=1, le=128)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    enable_api_docs: bool | None = None
    reader_database_url: SecretStr | None = None
    web_workers: int = Field(default=1, ge=1, le=8)
    trusted_proxy_ips: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("trusted_proxy_ips")
    @classmethod
    def validate_proxy_ips(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                network = ip_network(value, strict=False)
                if network.prefixlen == 0:
                    raise ValueError("Universal proxy trust is not allowed")
            except ValueError as exc:
                raise ValueError(
                    "Trusted proxies must be explicit IP addresses or CIDR networks"
                ) from exc
        return values

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

    @field_validator("allowed_hosts")
    @classmethod
    def validate_hosts(cls, value: list[str]) -> list[str]:
        if not value or any(
            not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?", host)
            or ".." in host
            for host in value
        ):
            raise ValueError("Allowed hosts must be explicit hostnames without ports or wildcards")
        return [host.lower() for host in value]

    @model_validator(mode="after")
    def validate_production_credentials(self) -> "Settings":
        if self.environment == "production":
            parsed = make_url(self.database_url.get_secret_value())
            if (
                not parsed.password
                or len(parsed.password) < 16
                or parsed.password == "winddesk_local"
            ):
                raise ValueError(
                    "Production requires separate database credentials (16+ characters)"
                )
            if "allowed_hosts" not in self.model_fields_set:
                raise ValueError("Production requires explicit GRID_ALLOWED_HOSTS")
            if parsed.host not in {"localhost", "127.0.0.1"} and parsed.query.get(
                "sslmode"
            ) not in {"verify-full", "verify-ca"}:
                raise ValueError("Production database connections require verified TLS")
            if not self.api_rate_limit_enabled:
                raise ValueError("Production request rate limiting must remain enabled")
            # The platform supplies these server-side values. Never derive host
            # permission from request headers, forwarding headers, or URL input.
            if os.environ.get("VERCEL") == "1":
                deployment_hosts = [
                    os.environ[name]
                    for name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL")
                    if os.environ.get(name)
                ]
                self.allowed_hosts = (
                    list(dict.fromkeys(self.allowed_hosts + self.validate_hosts(deployment_hosts)))
                    if deployment_hosts
                    else self.allowed_hosts
                )
        return self
