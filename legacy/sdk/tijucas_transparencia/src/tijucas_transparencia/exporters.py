from __future__ import annotations
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
