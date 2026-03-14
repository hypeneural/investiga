"""SQLAlchemy models for schema: risk."""

from datetime import datetime

from sqlalchemy import Integer, Numeric, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from investiga_repositories.postgres.session import Base


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="open")
    priority: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class CaseEntity(Base):
    __tablename__ = "case_entities"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("risk.cases.id"), nullable=False)
    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    role: Mapped[str | None] = mapped_column(String)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_code: Mapped[str] = mapped_column(String, nullable=False)
    claim_type: Mapped[str | None] = mapped_column(String)
    evidence_tier: Mapped[str | None] = mapped_column(String)
    party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("risk.cases.id"))
    description: Mapped[str | None] = mapped_column(Text)
    score_impact: Mapped[int | None] = mapped_column(Integer)
    source_rule_version: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    risco_financeiro: Mapped[int | None] = mapped_column(Integer)
    risco_relacional: Mapped[int | None] = mapped_column(Integer)
    evidencia: Mapped[int | None] = mapped_column(Integer)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.parties.id"), nullable=False)
    node_type: Mapped[str | None] = mapped_column(String)
    label: Mapped[str | None] = mapped_column(String)
    metadata: Mapped[dict | None] = mapped_column(JSONB)


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("risk.graph_nodes.id"), nullable=False)
    to_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("risk.graph_nodes.id"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String, nullable=False)
    weight: Mapped[float | None] = mapped_column(Numeric(5, 2))
    evidence_json: Mapped[dict | None] = mapped_column(JSONB)
    source_rule: Mapped[str | None] = mapped_column(String)


class RuleExecution(Base):
    __tablename__ = "rule_executions"
    __table_args__ = {"schema": "risk"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_code: Mapped[str] = mapped_column(String, nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String)
    target_party_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("core.parties.id"))
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    result_status: Mapped[str | None] = mapped_column(String)
    alerts_generated: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
