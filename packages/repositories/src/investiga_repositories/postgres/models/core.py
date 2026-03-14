"""SQLAlchemy models for schema: core."""

from datetime import datetime

from sqlalchemy import Boolean, Integer, Numeric, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from investiga_repositories.postgres.session import Base


class Party(Base):
    __tablename__ = "parties"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_type: Mapped[str] = mapped_column(String, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class PartyDocument(Base):
    __tablename__ = "party_documents"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    doc_value: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = {"schema": "core"}

    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String)
    cpf_center: Mapped[str | None] = mapped_column(String)
    surnames: Mapped[list[str] | None] = mapped_column(ARRAY(String))


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "core"}

    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), primary_key=True)
    razao_social: Mapped[str | None] = mapped_column(String)
    nome_fantasia: Mapped[str | None] = mapped_column(String)
    cnpj: Mapped[str | None] = mapped_column(String, unique=True)
    cnae_fiscal: Mapped[int | None] = mapped_column(Integer)
    cnae_descricao: Mapped[str | None] = mapped_column(String)
    natureza_juridica: Mapped[str | None] = mapped_column(String)
    capital_social: Mapped[float | None] = mapped_column(Numeric(15, 2))
    data_abertura: Mapped[datetime | None] = mapped_column(Date)
    situacao_cadastral: Mapped[str | None] = mapped_column(String)
    uf: Mapped[str | None] = mapped_column(String)
    municipio: Mapped[str | None] = mapped_column(String)


class PublicBody(Base):
    __tablename__ = "public_bodies"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    codigo: Mapped[str | None] = mapped_column(String)
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String)


class PublicUnit(Base):
    __tablename__ = "public_units"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.public_bodies.id"))
    codigo: Mapped[str | None] = mapped_column(String)
    descricao: Mapped[str] = mapped_column(String, nullable=False)


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    matricula: Mapped[str | None] = mapped_column(String)
    cargo: Mapped[str | None] = mapped_column(String)
    funcao: Mapped[str | None] = mapped_column(String)
    centro_custo: Mapped[str | None] = mapped_column(String)
    unit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.public_units.id"))
    salario_base: Mapped[float | None] = mapped_column(Numeric(15, 2))
    situacao: Mapped[str | None] = mapped_column(String)
    regime: Mapped[str | None] = mapped_column(String)
    admissao: Mapped[datetime | None] = mapped_column(Date)
    raw_id: Mapped[int | None] = mapped_column(Integer)


class ExpenseEvent(Base):
    __tablename__ = "expense_events"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    counterparty_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    orgao: Mapped[str | None] = mapped_column(String)
    unidade: Mapped[str | None] = mapped_column(String)
    valor_empenhado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_liquidado: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_pago: Mapped[float | None] = mapped_column(Numeric(15, 2))
    data_pagamento: Mapped[datetime | None] = mapped_column(Date)
    historico: Mapped[str | None] = mapped_column(Text)
    fonte_recurso: Mapped[str | None] = mapped_column(String)
    raw_id: Mapped[int | None] = mapped_column(Integer)


class PartyRelationship(Base):
    __tablename__ = "party_relationships"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    to_party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    rel_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    evidence_tier: Mapped[str | None] = mapped_column(String)
    source_rule: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class IdentityMatch(Base):
    __tablename__ = "identity_matches"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    party_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    match_method: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
