"""Minha Receita Source Adapter."""

import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from investiga_api.settings import settings
from investiga_connectors.base.adapter import SourceAdapter
from investiga_connectors.base.blocking import DefaultHttpDetector, BlockState

logger = logging.getLogger(__name__)


class MinhaReceitaCompanyDto(BaseModel):
    """Data Transfer Object for Minha Receita response."""
    model_config = ConfigDict(extra="ignore")

    cnpj: str
    razao_social: str | None = None
    nome_fantasia: str | None = None
    identificador_socio: int | None = None
    codigo_natureza_juridica: int | None = None
    data_inicio_atividade: str | None = None
    cnae_fiscal: int | None = None
    cnae_fiscal_descricao: str | None = None
    descricao_situacao_cadastral: str | None = None
    data_situacao_cadastral: str | None = None
    qsa: list[dict[str, Any]] = Field(default_factory=list)
    cnaes_secundarios: list[dict[str, Any]] = Field(default_factory=list)


class MinhaReceitaAdapter(SourceAdapter):
    """Adapter for MinhaReceita.org public API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.detector = DefaultHttpDetector()

    @property
    def source_name(self) -> str:
        return "minha_receita"

    async def ping(self) -> bool:
        """Check if Minha Receita is online."""
        try:
            async with self._get_client() as client:
                res = await client.get("/")
                return res.status_code == 200
        except Exception:
            return False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(
            base_url=settings.minha_receita_base_url,
            timeout=settings.timeout_minha_receita,
        )

    async def extract(self, cnpj: str) -> dict[str, Any]:
        """Fetch company data by CNPJ."""
        clean_cnpj = "".join(filter(str.isdigit, cnpj))
        
        async with self._get_client() as client:
            logger.debug(f"Fetching Minha Receita for CNPJ {clean_cnpj}")
            response = await client.get(f"/{clean_cnpj}")
            
            # Check for generic blocks (429, etc)
            block_state: BlockState = self.detector.detect(response)
            if block_state.is_blocked:
                # In a real flow, integration with SessionManager happens in the worker/job
                # Here we just raise for the retry policy to catch
                from investiga_orchestration.retry.policies import RateLimitError, SourceBlockedError
                if block_state.block_type == "rate_limit":
                    raise RateLimitError(block_state.message)
                raise SourceBlockedError(block_state.message)
                
            response.raise_for_status()
            return response.json()

    def parse(self, raw_payload: dict[str, Any]) -> MinhaReceitaCompanyDto:
        """Parse raw JSON into DTO."""
        return MinhaReceitaCompanyDto.model_validate(raw_payload)
