"""SQLAlchemy models for schema: enrich."""

from datetime import datetime

from sqlalchemy import Integer, Numeric, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from investiga_repositories.postgres.session import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    cnpj: Mapped[str] = mapped_column(String, nullable=False)
    razao_social: Mapped[str | None] = mapped_column(String)
    nome_fantasia: Mapped[str | None] = mapped_column(String)
    situacao_cadastral: Mapped[str | None] = mapped_column(String)
    data_situacao: Mapped[datetime | None] = mapped_column(Date)
    cnae_fiscal: Mapped[int | None] = mapped_column(Integer)
    cnae_descricao: Mapped[str | None] = mapped_column(String)
    natureza_juridica: Mapped[str | None] = mapped_column(String)
    capital_social: Mapped[float | None] = mapped_column(Numeric(15, 2))
    porte: Mapped[str | None] = mapped_column(String)
    uf: Mapped[str | None] = mapped_column(String)
    municipio: Mapped[str | None] = mapped_column(String)
    logradouro: Mapped[str | None] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class CompanyQsaMember(Base):
    __tablename__ = "company_qsa_members"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("enrich.company_profiles.id"))
    nome_socio: Mapped[str | None] = mapped_column(String)
    cnpj_cpf_socio: Mapped[str | None] = mapped_column(String)
    qualificacao: Mapped[str | None] = mapped_column(String)
    data_entrada: Mapped[datetime | None] = mapped_column(Date)


class CompanyCnae(Base):
    __tablename__ = "company_cnaes"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("enrich.company_profiles.id"))
    cnae_codigo: Mapped[int | None] = mapped_column(Integer)
    cnae_descricao: Mapped[str | None] = mapped_column(String)


class Sanction(Base):
    __tablename__ = "sanctions"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    source_list: Mapped[str] = mapped_column(String, nullable=False)
    sanction_type: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime | None] = mapped_column(Date)
    end_date: Mapped[datetime | None] = mapped_column(Date)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class PepFlag(Base):
    __tablename__ = "pep_flags"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    nome: Mapped[str | None] = mapped_column(String)
    cpf: Mapped[str | None] = mapped_column(String)
    cargo: Mapped[str | None] = mapped_column(String)
    orgao: Mapped[str | None] = mapped_column(String)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class SemanticLabel(Base):
    __tablename__ = "semantic_labels"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_event_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.expense_events.id"))
    label: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    grau_genericidade: Mapped[str | None] = mapped_column(String)
    compatibilidade_cnae: Mapped[str | None] = mapped_column(String)
    red_flags: Mapped[dict | None] = mapped_column(JSONB)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class LlmInference(Base):
    __tablename__ = "llm_inferences"
    __table_args__ = {"schema": "enrich"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    task_version: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    input_hash: Mapped[str] = mapped_column(String, nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String)
    final_model_used: Mapped[str | None] = mapped_column(String)
    model_attempts: Mapped[dict | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage_input: Mapped[int | None] = mapped_column(Integer)
    token_usage_output: Mapped[int | None] = mapped_column(Integer)
    cost_estimate: Mapped[float | None] = mapped_column(Numeric(10, 6))
    parse_status: Mapped[str | None] = mapped_column(String)
    parsed_output: Mapped[dict | None] = mapped_column(JSONB)
    raw_response_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
