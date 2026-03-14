import os
from pathlib import Path

base_dir = Path("C:/Users/Usuario/.gemini/antigravity/scratch/tijucas_transparencia")

files_to_create = {
    "pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "tijucas-transparencia"
version = "0.1.0"
description = "SDK para a API de Transparência de Tijucas"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "requests",
    "pandas",
    "python-dateutil",
    "tenacity",
    "pyarrow",
]
""",
    "README.md": "# Tijucas Transparencia SDK\n\nClient para a API de Transparência da Prefeitura de Tijucas.",
    ".env.example": "",
    "data/raw/.gitkeep": "",
    "data/processed/.gitkeep": "",
    "data/cache/.gitkeep": "",
    "src/tijucas_transparencia/__init__.py": """from .config import APIConfig
from .http_client import BaseHTTPClient
from .endpoints.pessoal import PessoalEndpoint
from .endpoints.dados_abertos import DadosAbertosEndpoint

class TijucasTransparenciaClient:
    def __init__(self, config: APIConfig | None = None):
        self.http = BaseHTTPClient(config=config)
        self.pessoal = PessoalEndpoint(self.http)
        self.dados_abertos = DadosAbertosEndpoint(self.http)
""",
    "src/tijucas_transparencia/config.py": """from dataclasses import dataclass

@dataclass(frozen=True)
class APIConfig:
    base_url: str = "https://tijucas.atende.net/api"
    timeout: int = 30
    user_agent: str = "TijucasTransparenciaClient/1.0"
    max_retries: int = 3
""",
    "src/tijucas_transparencia/exceptions.py": """class APIError(Exception):
    \"\"\"Erro genérico da API.\"\"\"

class APIResponseError(APIError):
    \"\"\"Resposta inválida ou inesperada da API.\"\"\"

class APIValidationError(APIError):
    \"\"\"Erro de validação de parâmetros.\"\"\"
""",
    "src/tijucas_transparencia/utils.py": """from __future__ import annotations
from datetime import datetime, date
from typing import Optional, Union

DateLike = Union[str, datetime, date]

def to_br_date(value: Optional[DateLike]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    value = str(value).strip()
    if not value:
        return None
    if len(value) == 10 and value[2] == "/" and value[5] == "/":
        return value
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        raise ValueError(f"Data inválida: {value}")

def parse_decimal_br(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)
""",
    "src/tijucas_transparencia/http_client.py": """from __future__ import annotations
from typing import Any, Dict, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from .config import APIConfig
from .exceptions import APIError, APIResponseError

class BaseHTTPClient:
    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
        })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((requests.RequestException, APIResponseError)),
        reraise=True,
    )
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise APIError(f"Erro HTTP ao acessar {url}: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise APIResponseError(
                f"Resposta não é JSON válido em {url}. Status={response.status_code}"
            ) from exc
""",
    "src/tijucas_transparencia/normalizers.py": """from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from .utils import parse_decimal_br

def normalize_funcionario(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    item["salarioBaseValor"] = parse_decimal_br(item.get("salarioBase"))
    item["admissaoDate"] = pd.to_datetime(
        item.get("admissao"),
        format="%d/%m/%Y",
        errors="coerce",
    )
    item["dataRescisaoDate"] = pd.to_datetime(
        item.get("dataRescisao"),
        format="%d/%m/%Y",
        errors="coerce",
    )
    item["paginaAtual"] = _to_int(item.get("paginaAtual"))
    item["totalPaginas"] = _to_int(item.get("totalPaginas"))
    item["totalRegistros"] = _to_int(item.get("totalRegistros"))
    return item

def normalize_wcp_item(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    for key, value in list(item.items()):
        if key.lower().startswith("valor"):
            try:
                item[key] = float(value)
            except (TypeError, ValueError):
                pass
    return item

def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
""",
    "src/tijucas_transparencia/pagination.py": """from __future__ import annotations
from typing import Callable, Dict, Any, List

def collect_paginated(fetch_page: Callable[[int], Dict[str, Any]]) -> List[Dict[str, Any]]:
    first_page = fetch_page(1)
    items = list(first_page["items"])
    total_pages = int(first_page.get("total_pages") or 1)

    for page in range(2, total_pages + 1):
        page_data = fetch_page(page)
        items.extend(page_data["items"])

    return items
""",
    "src/tijucas_transparencia/endpoints/__init__.py": "",
    "src/tijucas_transparencia/endpoints/pessoal.py": """from __future__ import annotations
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

        if not isinstance(payload, list):
            raise APIResponseError(
                "Formato inesperado no endpoint de funcionários. Esperado lista JSON."
            )

        normalized_items = [normalize_funcionario(item) for item in payload]
        meta_source = normalized_items[0] if normalized_items else {}
        return {
            "items": normalized_items,
            "page": meta_source.get("paginaAtual", pagina),
            "total_pages": meta_source.get("totalPaginas", 1),
            "total_records": meta_source.get("totalRegistros", len(normalized_items)),
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
""",
    "src/tijucas_transparencia/endpoints/dados_abertos.py": """from __future__ import annotations
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
""",
    "src/tijucas_transparencia/filters.py": """from __future__ import annotations
import pandas as pd

def filtrar_funcionarios(
    df: pd.DataFrame,
    situacao: str | None = None,
    nome_contains: str | None = None,
    cargo_contains: str | None = None,
    funcao_contains: str | None = None,
    local_contains: str | None = None,
    centro_custo_contains: str | None = None,
    salario_min: float | None = None,
    salario_max: float | None = None,
) -> pd.DataFrame:
    result = df.copy()
    if situacao:
        result = result[
            result["situacao"].fillna("").str.lower() == situacao.lower()
        ]
    if nome_contains:
        result = result[
            result["nome"].fillna("").str.contains(nome_contains, case=False, na=False)
        ]
    if cargo_contains:
        result = result[
            result["cargo"].fillna("").str.contains(cargo_contains, case=False, na=False)
        ]
    if funcao_contains:
        result = result[
            result["funcao"].fillna("").str.contains(funcao_contains, case=False, na=False)
        ]
    if local_contains:
        result = result[
            result["localTrabalho"].fillna("").str.contains(local_contains, case=False, na=False)
        ]
    if centro_custo_contains:
        result = result[
            result["centroCusto"].fillna("").str.contains(centro_custo_contains, case=False, na=False)
        ]
    if salario_min is not None:
        result = result[result["salarioBaseValor"] >= salario_min]
    if salario_max is not None:
        result = result[result["salarioBaseValor"] <= salario_max]
    return result
""",
    "src/tijucas_transparencia/exporters.py": """from __future__ import annotations
from pathlib import Path
import pandas as pd

def export_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

def export_excel(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if "dataRescisaoDate" in df.columns:
        df["dataRescisaoDate"] = df["dataRescisaoDate"].dt.tz_localize(None)
    if "admissaoDate" in df.columns:
        df["admissaoDate"] = df["admissaoDate"].dt.tz_localize(None)
    df.to_excel(path, index=False)

def export_parquet(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
""",
    "scripts/fetch_funcionarios.py": """import argparse
from datetime import date
from src.tijucas_transparencia import TijucasTransparenciaClient
from src.tijucas_transparencia.exporters import export_csv, export_excel

def main():
    parser = argparse.ArgumentParser(description="Busca funcionários no Portal de Transparência.")
    parser.add_argument("--tipo-busca", type=int, default=1, choices=[1, 2, 3], help="1: Ativos, 2: Desligados, 3: Todos")
    parser.add_argument("--desligamento-inicio", type=str, help="Data inicial de desligamento (DD/MM/AAAA)")
    parser.add_argument("--desligamento-final", type=str, help="Data final de desligamento (DD/MM/AAAA)")
    args = parser.parse_args()

    client = TijucasTransparenciaClient()

    print(f"Buscando com tipo_busca={args.tipo_busca}...")
    df = client.pessoal.get_funcionarios_df(
        tipo_busca=args.tipo_busca,
        desligamento_inicio=args.desligamento_inicio,
        desligamento_final=args.desligamento_final
    )

    print("Total carregado:", len(df))
    if len(df) > 0:
        print("Amostra:")
        print(df[["nome", "cargo", "salarioBaseValor"]].head(5).to_string())

    today = date.today().isoformat()
    csv_path = f"data/processed/funcionarios_{today}.csv"
    export_csv(df, csv_path)
    print(f"Arquivo CSV salvo em: {csv_path}")

if __name__ == "__main__":
    main()
""",
    "scripts/demo_filters.py": """from src.tijucas_transparencia import TijucasTransparenciaClient
from src.tijucas_transparencia.filters import filtrar_funcionarios

def main():
    client = TijucasTransparenciaClient()

    print("Buscando funcionários...")
    df = client.pessoal.get_funcionarios_df(tipo_busca=1)

    print(f"Total: {len(df)}")

    professores = filtrar_funcionarios(
        df,
        situacao="Trabalhando",
        cargo_contains="Professor",
    )
    print("\\n=== Professores ===")
    print(f"Total: {len(professores)}")
    print(professores[["nome", "cargo", "localTrabalho", "salarioBaseValor"]].head(5).to_string())

    saude = filtrar_funcionarios(
        df,
        local_contains="saúde",
    )
    print("\\n=== Pessoal da Saúde ===")
    print(f"Total: {len(saude)}")
    print(saude[["nome", "cargo", "localTrabalho"]].head(5).to_string())

if __name__ == "__main__":
    main()
"""
}

for rel_path, content in files_to_create.items():
    p = base_dir / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

print(f"Created project at {base_dir}")
