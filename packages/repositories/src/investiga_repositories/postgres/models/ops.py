"""SQLAlchemy models for schema: ops."""

from datetime import datetime
import uuid

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from investiga_repositories.postgres.session import Base


class SourceSession(Base):
    __tablename__ = "source_sessions"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    session_mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ready")
    browser_profile_name: Mapped[str | None] = mapped_column(String)
    cookie_version: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_validation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String)
    last_error_message: Mapped[str | None] = mapped_column(Text)
    checkpoint_json: Mapped[dict | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    payload: Mapped[dict | None] = mapped_column(JSONB)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_name: Mapped[str | None] = mapped_column(String)
    source_session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ops.source_sessions.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ops.jobs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    worker_name: Mapped[str | None] = mapped_column(String)
    attempt: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    context_json: Mapped[dict | None] = mapped_column(JSONB)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class HumanIntervention(Base):
    __tablename__ = "human_interventions"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ops.source_sessions.id"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ops.jobs.id"))
    intervention_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by: Mapped[str | None] = mapped_column(String)
    resolved_by: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    artifacts_json: Mapped[dict | None] = mapped_column(JSONB)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_name: Mapped[str] = mapped_column(String, nullable=False)
    queue_name: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="alive")
    last_beat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    jobs_processed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String)
    requests_per_minute: Mapped[int | None] = mapped_column(Integer)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class DeadLetter(Base):
    __tablename__ = "dead_letters"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_queue: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ops.jobs.id"))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    failure_type: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int | None] = mapped_column(Integer)
    dead_lettered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
