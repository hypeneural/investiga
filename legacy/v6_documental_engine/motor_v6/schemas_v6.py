from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import date, datetime

@dataclass
class EvidenceTier:
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"

@dataclass
class Severity:
    CRITICAL = "critica"
    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baixa"

@dataclass
class ClaimType:
    FATO_OBJETIVO = "fato_objetivo"
    PADRAO_SUSPEITO = "padrao_suspeito"
    HIPOTESE_RELACIONAL = "hipotese_relacional"

@dataclass
class TargetEvent:
    """Representa a admissão de um alvo político ou servidor vinculado."""
    target_id: str
    nome: str
    cpf: str
    cargo: str
    admissao: Optional[date]
    raw_payload: dict = field(default_factory=dict)

@dataclass
class PaymentEvent:
    """Representa o evento financeiro macro vindo de despesas."""
    payment_id: str
    source: str
    orgao_codigo: Optional[str]
    orgao_descricao: Optional[str]
    unidade_codigo: Optional[str]
    unidade_descricao: Optional[str]
    credor_nome_raw: str
    credor_documento_raw: str
    credor_documento_num: str
    credor_documento_tipo: str # CPF, CNPJ, UNKNOWN
    credor_raiz_cnpj: Optional[str]
    valor_pago: float
    data_pagamento: Optional[date]
    data_liquidacao: Optional[date]
    data_empenho: Optional[date]
    empenho_numero: Optional[str]
    empenho_ano: Optional[str]
    liquidacao_sequencia: Optional[str]
    liquidacao_tipo: Optional[str]
    liquidacao_ano: Optional[str]
    raw_payload: dict = field(default_factory=dict)

@dataclass
class LiquidationDocument:
    """Representa a NF ou documento real extraído do detalhe."""
    document_id: str
    source: str
    payment_id_hint: Optional[str]
    loa_ano: Optional[str]
    liquidacao_sequencia: Optional[str]
    liquidacao_tipo: Optional[str]
    credor_documento_raw: str
    credor_documento_num: str
    credor_documento_tipo: str # CPF, CNPJ, UNKNOWN
    credor_raiz_cnpj: Optional[str]
    numero_documento: Optional[str]
    tipo_documento: Optional[str]
    data_documento: Optional[date]
    valor_documento: float
    raw_payload: dict = field(default_factory=dict)

@dataclass
class CompanyProfile:
    """Representa a empresa consultada na base societária (Receita)."""
    cnpj: str
    cnpj_raiz: str
    razao_social: Optional[str]
    data_inicio_atividade: Optional[date]
    situacao_cadastral: Optional[str]
    cnae_principal_codigo: Optional[str]
    qsa: List[dict] = field(default_factory=list)
    raw_payload: dict = field(default_factory=dict)

@dataclass
class AlertEvent:
    """O schema unificado de saída de detecção."""
    alert_id: str
    rule_code: str
    claim_type: str
    evidence_tier: str
    severity: str
    title: str
    description: str
    explanation: str
    score_financeiro: int = 0
    score_relacional: int = 0
    requires_manual_review: bool = True
    target_id: Optional[str] = None
    payment_id: Optional[str] = None
    document_id: Optional[str] = None
    company_cnpj: Optional[str] = None
    evidence: dict = field(default_factory=dict)
    audit_steps: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            "alert_id": self.alert_id,
            "rule_code": self.rule_code,
            "claim_type": self.claim_type,
            "evidence_tier": self.evidence_tier,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "explanation": self.explanation,
            "score_financeiro": self.score_financeiro,
            "score_relacional": self.score_relacional,
            "requires_manual_review": self.requires_manual_review,
            "target_id": self.target_id,
            "payment_id": self.payment_id,
            "document_id": self.document_id,
            "company_cnpj": self.company_cnpj,
            "evidence": self.evidence,
            "audit_steps": self.audit_steps,
            "created_at": self.created_at.isoformat()
        }
