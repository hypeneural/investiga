from __future__ import annotations
from typing import Dict, Any, Optional
import pandas as pd

from ..exceptions import APIResponseError
from ..http_client import BaseHTTPClient
from ..normalizers import normalize_wcp_item
from ..utils import to_br_date

class DadosAbertosEndpoint:
    BASE = "WCPDadosAbertos"

    def __init__(self, client: BaseHTTPClient):
        self.client = client

    def _get_wcp(self, route: str, params: Dict[str, Any]) -> pd.DataFrame:
        payload = self.client.get(f"{self.BASE}/{route}", params=params)

        if not isinstance(payload, dict):
            raise APIResponseError("Formato inesperado no endpoint WCPDadosAbertos.")

        retorno = payload.get("retorno", [])
        if not isinstance(retorno, list):
            raise APIResponseError("Campo 'retorno' inválido no endpoint WCPDadosAbertos.")

        return pd.DataFrame([normalize_wcp_item(item) for item in retorno])

    def despesas(self, data_inicial: str, data_final: str) -> pd.DataFrame:
        return self._get_wcp(
            "despesas",
            {
                "dataInicial": to_br_date(data_inicial),
                "dataFinal": to_br_date(data_final),
            },
        )

    def despesa_restos(self, data_final: str) -> pd.DataFrame:
        return self._get_wcp(
            "despesaRestos",
            {
                "dataFinal": to_br_date(data_final),
            },
        )

    def despesas_orcadas(self, data_final: str) -> pd.DataFrame:
        return self._get_wcp(
            "despesasOrcadas",
            {
                "dataFinal": to_br_date(data_final),
            },
        )

    def receitas(self, data_inicial: str, data_final: str) -> pd.DataFrame:
        return self._get_wcp(
            "receitas",
            {
                "dataInicial": to_br_date(data_inicial),
                "dataFinal": to_br_date(data_final),
            },
        )

    def receitas_orcadas(self, data_final: str) -> pd.DataFrame:
        return self._get_wcp(
            "receitasOrcadas",
            {
                "dataFinal": to_br_date(data_final),
            },
        )
