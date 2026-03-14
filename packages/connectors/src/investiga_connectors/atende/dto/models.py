"""Data Transfer Objects for Atende responses."""

from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class AtendePaymentDto(BaseModel):
    """Normalized Atende Payment."""
    model_config = ConfigDict(extra="ignore")

    codigo_empenho: str | None = None
    ano_empenho: int | None = None
    credor_documento: str | None = None
    credor_nome: str | None = None
    valor_empenhado: float = 0.0
    valor_liquidado: float = 0.0
    valor_pago: float = 0.0
    data_emissao: date | None = None
    data_pagamento: date | None = None
    orgao: str | None = None
    unidade: str | None = None
    historico: str | None = None
    fonte_recurso: str | None = None
    modalidade: str | None = None


class AtendeEmployeeDto(BaseModel):
    """Normalized Atende Employee."""
    model_config = ConfigDict(extra="ignore")

    nome: str
    cpf_mascarado: str | None = None
    matricula: str | None = None
    cargo: str | None = None
    funcao: str | None = None
    centro_custo: str | None = None
    salario_base: float = 0.0
    salario_bruto: float = 0.0
    salario_liquido: float = 0.0
    situacao: str | None = None
    regime: str | None = None
    data_admissao: date | None = None
    competencia: str | None = None  # MM/YYYY
