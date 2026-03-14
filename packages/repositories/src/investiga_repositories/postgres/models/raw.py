"""SQLAlchemy models for schema: raw."""

from datetime import datetime

from sqlalchemy import Integer, Numeric, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from investiga_repositories.postgres.session import Base


class SourceRun(Base):
    __tablename__ = "source_runs"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    trigger_type: Mapped[str | None] = mapped_column(String)  # manual, cron, replay
    job_id: Mapped[str | None] = mapped_column(String)
    correlation_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")
    checkpoint_json: Mapped[dict | None] = mapped_column(JSONB)
    request_params_json: Mapped[dict | None] = mapped_column(JSONB)
    stats_json: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class AtendePayment(Base):
    __tablename__ = "atende_payments"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw.source_runs.id"))
    external_id: Mapped[str | None] = mapped_column(String)
    credor_documento: Mapped[str | None] = mapped_column(String)
    credor_nome: Mapped[str | None] = mapped_column(String)
    valor_empenhado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_liquidado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_pago: Mapped[float | None] = mapped_column(Numeric(15, 2))
    data_pagamento: Mapped[datetime | None] = mapped_column(Date)
    orgao_descricao: Mapped[str | None] = mapped_column(String)
    unidade_descricao: Mapped[str | None] = mapped_column(String)
    fonte_recurso: Mapped[str | None] = mapped_column(String)
    modalidade: Mapped[str | None] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    payload_hash: Mapped[str | None] = mapped_column(String)
    normalization_status: Mapped[str] = mapped_column(String, default="pending")
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class AtendeEmployee(Base):
    __tablename__ = "atende_employees"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw.source_runs.id"))
    nome: Mapped[str | None] = mapped_column(String)
    cpf_masked: Mapped[str | None] = mapped_column(String)
    matricula: Mapped[str | None] = mapped_column(String)
    cargo: Mapped[str | None] = mapped_column(String)
    salario_base: Mapped[float | None] = mapped_column(Numeric(15, 2))
    centro_custo: Mapped[str | None] = mapped_column(String)
    situacao: Mapped[str | None] = mapped_column(String)
    regime: Mapped[str | None] = mapped_column(String)
    admissao: Mapped[datetime | None] = mapped_column(Date)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    payload_hash: Mapped[str | None] = mapped_column(String)
    normalization_status: Mapped[str] = mapped_column(String, default="pending")
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class MinhaReceitaPayload(Base):
    __tablename__ = "minha_receita_payloads"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw.source_runs.id"))
    cnpj: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String)
    normalization_status: Mapped[str] = mapped_column(String, default="pending")
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class OpenRouterResponse(Base):
    __tablename__ = "openrouter_responses"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw.source_runs.id"))
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    input_hash: Mapped[str] = mapped_column(String, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String)
    response_json: Mapped[dict | None] = mapped_column(JSONB)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String)
    content_text: Mapped[str | None] = mapped_column(Text)
    job_id: Mapped[str | None] = mapped_column(String)  # UUID string matching job
    source_session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ops.source_sessions.id"))
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("raw.source_runs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
