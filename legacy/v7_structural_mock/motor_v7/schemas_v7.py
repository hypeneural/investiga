from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import date, datetime
import hashlib

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

@dataclass
class EmissaoEmpenho:
    """O novo Evento V7 focado estruturalmente na despesa e contrato (Lote)."""
    id_pagamento: str
    empenho_numero: Optional[str]
    empenho_ano: Optional[str]
    data_emissao: Optional[date]
    credor_cnpj: str
    credor_nome: str
    
    # Orçamentário e Licitatório
    orgao_descricao: Optional[str]
    unidade_descricao: Optional[str]
    acao: Optional[str]
    despesa: Optional[str]
    modalidade: Optional[str]
    
    # Processo / Contrato
    licitacao_numero: Optional[str]
    data_homologacao: Optional[date]
    contrato_numero: Optional[str]
    aditivo_numero: Optional[str]
    
    # Descrição do Objeto
    historico: Optional[str]
    
    # Valores
    valor_empenho: float
    valor_retido: float
    
    # Dados Bancários (Rastreamento de Laranja)
    banco: Optional[str]
    agencia: Optional[str]
    conta: Optional[str]

    raw_payload: dict = field(default_factory=dict)

    # Propriedades Derivadas (Enriquecimento V7 Local)
    @property
    def credor_cnpj_raiz(self) -> Optional[str]:
        if self.credor_cnpj and len(self.credor_cnpj) >= 10:
            return "".join(filter(str.isdigit, self.credor_cnpj))[:8]
        return None

    @property
    def ano_mes_emissao(self) -> Optional[str]:
        if self.data_emissao:
            return f"{self.data_emissao.year}-{self.data_emissao.month:02d}"
        return None

    @property
    def percentual_retido(self) -> float:
        if self.valor_empenho > 0:
            return (self.valor_retido / self.valor_empenho) * 100.0
        return 0.0

    @property
    def historico_hash(self) -> str:
        h = self.historico or ""
        # Normalização crua: upper e strip
        h_norm = h.upper().strip()
        return hashlib.md5(h_norm.encode('utf-8')).hexdigest()

    @property
    def conta_bancaria_chave(self) -> Optional[str]:
        if self.banco and self.agencia and self.conta:
            return f"{self.banco}|{self.agencia}|{self.conta}"
        return None
        
    @property
    def dias_entre_homologacao_e_empenho(self) -> Optional[int]:
        if self.data_homologacao and self.data_emissao:
            delta = (self.data_emissao - self.data_homologacao).days
            return delta
        return None

@dataclass
class AlertV7:
    """Schema V7 para reports em Lote e Clusterizados."""
    regra: str
    severidade: str
    tier: str
    titulo: str
    descricao: str
    evidencias: dict = field(default_factory=dict)
    acao_auditoria: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "regra": self.regra,
            "severidade": self.severidade,
            "tier": self.tier,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "evidencias": self.evidencias,
            "acao_auditoria": self.acao_auditoria
        }
