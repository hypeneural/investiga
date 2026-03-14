from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd

from ..exceptions import APIValidationError, APIResponseError
from ..http_client import BaseHTTPClient
from ..normalizers import normalize_funcionario
from ..pagination import collect_paginated
from ..utils import to_br_date

class PessoalEndpoint:
    PATH_FUNCIONARIOS = "transparencia-pessoal-funcionarios"

    def __init__(self, client: BaseHTTPClient):
        self.client = client

    def _validate_funcionarios_params(
        self,
        tipo_busca: int,
        desligamento_inicio: Optional[str],
        desligamento_final: Optional[str],
    ) -> None:
        if tipo_busca not in (1, 2, 3):
            raise APIValidationError("tipo_busca deve ser 1, 2 ou 3.")
        if tipo_busca in (2, 3):
            if not desligamento_inicio or not desligamento_final:
                raise APIValidationError(
                    "Para tipo_busca=2 ou 3, desligamento_inicio e desligamento_final são obrigatórios."
                )

    def get_funcionarios_page(
        self,
        *,
        pagina: int = 1,
        tipo_busca: int = 1,
        admissao_inicio: Optional[str] = None,
        admissao_final: Optional[str] = None,
        desligamento_inicio: Optional[str] = None,
        desligamento_final: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._validate_funcionarios_params(
            tipo_busca=tipo_busca,
            desligamento_inicio=desligamento_inicio,
            desligamento_final=desligamento_final,
        )

        params: Dict[str, Any] = {
            "pagina": pagina,
            "tipoBusca": tipo_busca,
        }

        if admissao_inicio:
            params["admissaoInicio"] = to_br_date(admissao_inicio)
        if admissao_final:
            params["admissaoFinal"] = to_br_date(admissao_final)
        if desligamento_inicio:
            params["desligamentoInicio"] = to_br_date(desligamento_inicio)
        if desligamento_final:
            params["desligamentoFinal"] = to_br_date(desligamento_final)

        payload = self.client.get(self.PATH_FUNCIONARIOS, params=params)

        if not isinstance(payload, dict) or "registros" not in payload:
            raise APIResponseError(
                f"Formato inesperado no endpoint de funcionários. Esperado dict com 'registros'. Recebido: {type(payload)}."
            )

        items = payload.get("registros", [])
        normalized_items = [normalize_funcionario(item) for item in items]
        
        pagina_atual = payload.get("paginaAtual", pagina)
        total_paginas = payload.get("totalPaginas", 1)
        total_registros = payload.get("totalRegistros", len(normalized_items))

        return {
            "items": normalized_items,
            "page": int(pagina_atual) if pagina_atual is not None else pagina,
            "total_pages": int(total_paginas) if total_paginas is not None else 1,
            "total_records": int(total_registros) if total_registros is not None else len(normalized_items),
        }

    def get_all_funcionarios(
        self,
        *,
        tipo_busca: int = 1,
        admissao_inicio: Optional[str] = None,
        admissao_final: Optional[str] = None,
        desligamento_inicio: Optional[str] = None,
        desligamento_final: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return collect_paginated(
            lambda page: self.get_funcionarios_page(
                pagina=page,
                tipo_busca=tipo_busca,
                admissao_inicio=admissao_inicio,
                admissao_final=admissao_final,
                desligamento_inicio=desligamento_inicio,
                desligamento_final=desligamento_final,
            )
        )

    def get_funcionarios_df(self, **kwargs) -> pd.DataFrame:
        data = self.get_all_funcionarios(**kwargs)
        return pd.DataFrame(data)
