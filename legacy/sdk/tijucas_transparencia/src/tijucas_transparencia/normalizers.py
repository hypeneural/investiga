from __future__ import annotations
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
