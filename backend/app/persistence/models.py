"""Append-only source evidence, versioned releases, and a separately mutable active pointer."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    desc,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IngestionRun(Base):
    __tablename__ = "ingestion_run"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    archive_sha256: Mapped[str] = mapped_column(String(64))
    release_id: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(80))


class RawBatchRecord(Base):
    __tablename__ = "raw_batch"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(8))
    source_url: Mapped[str] = mapped_column(String(1024))
    parameters: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_gzip: Mapped[bytes] = mapped_column(LargeBinary)
    payload_bytes: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("dataset IN ('WINDFOR', 'FUELHH')"),)


class VersionColumns:
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generation_mw: Mapped[int | None] = mapped_column(BigInteger)
    quality_reason: Mapped[str | None] = mapped_column(String(80))


class ForecastVersion(VersionColumns, Base):
    __tablename__ = "forecast_version"
    __table_args__ = (
        Index(
            "ix_forecast_version_target_publication",
            "target_start_utc",
            desc("source_published_at"),
        ),
    )


class ActualVersion(VersionColumns, Base):
    __tablename__ = "actual_version"
    settlement_date: Mapped[date] = mapped_column(Date)
    settlement_period: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        Index(
            "ix_actual_version_target_publication", "target_start_utc", desc("source_published_at")
        ),
    )


class ForecastBatchMember(Base):
    __tablename__ = "forecast_batch_member"
    batch_id: Mapped[str] = mapped_column(ForeignKey("raw_batch.id"), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("forecast_version.id"), primary_key=True)


class ActualBatchMember(Base):
    __tablename__ = "actual_batch_member"
    batch_id: Mapped[str] = mapped_column(ForeignKey("raw_batch.id"), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("actual_version.id"), primary_key=True)


class DatasetRelease(Base):
    __tablename__ = "dataset_release"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    quality: Mapped[dict] = mapped_column(JSONB)
    parser_version: Mapped[str] = mapped_column(String(40))
    __table_args__ = (CheckConstraint("status IN ('accepted', 'rejected')"),)


class ReleaseBatchMember(Base):
    __tablename__ = "release_batch_member"
    release_id: Mapped[str] = mapped_column(ForeignKey("dataset_release.id"), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("raw_batch.id"), primary_key=True)


class ActiveRelease(Base):
    __tablename__ = "active_release"
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("dataset_release.id"))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReleaseForecastMember(Base):
    __tablename__ = "release_forecast_member"
    release_id: Mapped[str] = mapped_column(ForeignKey("dataset_release.id"), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("forecast_version.id"), primary_key=True)


class ReleaseActualMember(Base):
    __tablename__ = "release_actual_member"
    release_id: Mapped[str] = mapped_column(ForeignKey("dataset_release.id"), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("actual_version.id"), primary_key=True)
