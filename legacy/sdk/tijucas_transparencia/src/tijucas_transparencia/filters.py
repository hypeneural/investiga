from __future__ import annotations
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
