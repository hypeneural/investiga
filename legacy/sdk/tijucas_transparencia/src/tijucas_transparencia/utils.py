from __future__ import annotations
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
