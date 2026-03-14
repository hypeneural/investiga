"""
Script para buscar dados de despesas da API de Dados Abertos de Tijucas (SC).

Endpoints:
  1. /despesas            - Despesas (requer dataInicial + dataFinal, mesmo exercício)
  2. /despesaRestos       - Despesas com Restos a Pagar (requer dataFinal)
  3. /despesasOrcadas     - Despesas Orçadas (requer dataFinal)

Busca dados de 2025 (ano completo) e 2026 (até hoje).
Salva cada endpoint em um JSON separado e um consolidado.
"""
import urllib.request
import urllib.error
import json
import time
import ssl
import sys
import calendar
from datetime import datetime


BASE_URL = "https://tijucas.atende.net/api/WCPDadosAbertos"
TIMEOUT = 120

# Anos a buscar
CURRENT_YEAR = 2026
YEARS = [2022, 2023, 2024, 2025, 2026]


def fetch_url(url: str, label: str, retries: int = 15):
    """Faz GET na URL com retry e tratamento de rate limit."""
    ctx = ssl.create_default_context()
    for attempt in range(retries):
        try:
            print(f"  [{label}] Buscando...", end=" ", flush=True)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                status = data.get("status", "unknown")
                retorno = data.get("retorno", [])
                print(f"OK (status={status}, {len(retorno)} registros)")
                return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"Rate limit, aguardando {wait}s...")
                time.sleep(wait)
            else:
                body = ""
                try:
                    body = e.read().decode("utf-8")[:200]
                except Exception:
                    pass
                print(f"HTTP {e.code} (tentativa {attempt+1}/{retries}): {body}")
                if attempt < retries - 1:
                    time.sleep(3)
        except Exception as e:
            print(f"Erro (tentativa {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


def parse_value(val_str) -> float:
    """Converte string de valor para float."""
    if not val_str:
        return 0.0
    try:
        return float(str(val_str))
    except ValueError:
        return 0.0


def get_month_ranges(year: int) -> list:
    """Retorna lista de (dataInicial, dataFinal) para cada mês do ano."""
    now = datetime.now()
    ranges = []
    for month in range(1, 13):
        if year == CURRENT_YEAR and month > now.month:
            break
        last_day = calendar.monthrange(year, month)[1]
        if year == CURRENT_YEAR and month == now.month:
            last_day = now.day
        di = f"01/{month:02d}/{year}"
        df = f"{last_day:02d}/{month:02d}/{year}"
        ranges.append((di, df))
    return ranges


def fetch_despesas(year: int) -> list:
    """
    Busca despesas de um exercício inteiro, mês a mês.
    A API exige dataInicial e dataFinal no mesmo exercício.
    Usamos busca mensal para evitar respostas muito grandes.
    """
    all_records = []
    month_ranges = get_month_ranges(year)

    for di, df in month_ranges:
        # Build URL manually to avoid encoding slashes
        url = f"{BASE_URL}/despesas?dataInicial={di}&dataFinal={df}"
        label = f"despesas {di}-{df}"
        data = fetch_url(url, label)
        if data and data.get("status") == "ok":
            records = data.get("retorno", [])
            for r in records:
                r["_ano"] = year
                r["_mes"] = di.split("/")[1]
            all_records.extend(records)
        time.sleep(1.5)
    return all_records


def fetch_despesa_restos(year: int) -> list:
    """Busca restos a pagar até o final do ano (ou até hoje)."""
    if year == CURRENT_YEAR:
        data_final = datetime.now().strftime("%d/%m/%Y")
    else:
        data_final = f"31/12/{year}"

    url = f"{BASE_URL}/despesaRestos?dataFinal={data_final}"
    label = f"despesaRestos {year} (até {data_final})"

    data = fetch_url(url, label)
    if data and data.get("status") == "ok":
        registros = data.get("retorno", [])
        for r in registros:
            r["_ano"] = year
        return registros
    return []


def fetch_despesas_orcadas(year: int) -> list:
    """Busca despesas orçadas do ano."""
    if year == CURRENT_YEAR:
        data_final = datetime.now().strftime("%d/%m/%Y")
    else:
        data_final = f"31/12/{year}"

    url = f"{BASE_URL}/despesasOrcadas?dataFinal={data_final}"
    label = f"despesasOrcadas {year} (até {data_final})"

    data = fetch_url(url, label)
    if data and data.get("status") == "ok":
        registros = data.get("retorno", [])
        for r in registros:
            r["_ano"] = year
        return registros
    return []


def save_json(data, filename: str):
    """Salva dados em JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    import os
    size_kb = os.path.getsize(filename) / 1024
    print(f"  Salvo: {filename} ({size_kb:.1f} KB)")


def summarize_despesas(registros: list, label: str):
    """Imprime resumo das despesas."""
    if not registros:
        print(f"  {label}: Nenhum registro")
        return

    total_empenhado = sum(parse_value(r.get("valorEmpenhado", "0")) for r in registros)
    total_liquidado = sum(parse_value(r.get("valorLiquidado", "0")) for r in registros)
    total_pago = sum(parse_value(r.get("valorPago", "0")) for r in registros)

    print(f"  {label}: {len(registros)} registros")
    print(f"    Empenhado: R$ {total_empenhado:,.2f}")
    if total_liquidado > 0:
        print(f"    Liquidado: R$ {total_liquidado:,.2f}")
    print(f"    Pago:      R$ {total_pago:,.2f}")


def main():
    print("=" * 60)
    print("Busca de Despesas - Tijucas Dados Abertos")
    print(f"Data da consulta: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    all_despesas = []
    all_restos = []
    all_orcadas = []

    for year in YEARS:
        print(f"\n{'─' * 60}")
        print(f"ANO: {year}")
        print(f"{'─' * 60}")

        # 1. Despesas (mês a mês)
        print(f"\n1. Despesas {year} (mês a mês):")
        despesas = fetch_despesas(year)
        all_despesas.extend(despesas)
        time.sleep(2)

        # 2. Restos a Pagar
        print(f"\n2. Restos a Pagar {year}:")
        restos = fetch_despesa_restos(year)
        all_restos.extend(restos)
        time.sleep(2)

        # 3. Despesas Orçadas
        print(f"\n3. Despesas Orçadas {year}:")
        orcadas = fetch_despesas_orcadas(year)
        all_orcadas.extend(orcadas)
        time.sleep(2)

    # Salvar arquivos individuais
    print(f"\n{'=' * 60}")
    print("SALVANDO ARQUIVOS")
    print(f"{'=' * 60}")

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    despesas_output = {
        "totalRegistros": len(all_despesas),
        "anos": YEARS,
        "dataConsulta": timestamp,
        "registros": all_despesas,
    }
    save_json(despesas_output, "despesas.json")

    restos_output = {
        "totalRegistros": len(all_restos),
        "anos": YEARS,
        "dataConsulta": timestamp,
        "registros": all_restos,
    }
    save_json(restos_output, "despesas_restos.json")

    orcadas_output = {
        "totalRegistros": len(all_orcadas),
        "anos": YEARS,
        "dataConsulta": timestamp,
        "registros": all_orcadas,
    }
    save_json(orcadas_output, "despesas_orcadas.json")

    # Consolidado
    consolidado = {
        "dataConsulta": timestamp,
        "anos": YEARS,
        "despesas": despesas_output,
        "despesaRestos": restos_output,
        "despesasOrcadas": orcadas_output,
    }
    save_json(consolidado, "despesas_consolidado.json")

    # Resumo
    print(f"\n{'=' * 60}")
    print("RESUMO")
    print(f"{'=' * 60}")

    for year in YEARS:
        print(f"\n  Ano {year}:")
        desp_year = [r for r in all_despesas if r.get("_ano") == year]
        rest_year = [r for r in all_restos if r.get("_ano") == year]
        orcd_year = [r for r in all_orcadas if r.get("_ano") == year]
        summarize_despesas(desp_year, "Despesas")

        if rest_year:
            total_pagar = sum(parse_value(r.get("valorPagar", "0")) for r in rest_year)
            total_pago_r = sum(parse_value(r.get("valorPago", "0")) for r in rest_year)
            print(f"  Restos a Pagar: {len(rest_year)} registros")
            print(f"    A Pagar: R$ {total_pagar:,.2f}")
            print(f"    Pago:    R$ {total_pago_r:,.2f}")
        else:
            print(f"  Restos a Pagar: Nenhum registro")

        if orcd_year:
            total_orcado = sum(parse_value(r.get("valorOrcado", "0")) for r in orcd_year)
            print(f"  Despesas Orçadas: {len(orcd_year)} registros")
            print(f"    Orçado: R$ {total_orcado:,.2f}")
        else:
            print(f"  Despesas Orçadas: Nenhum registro")

    print(f"\n{'=' * 60}")
    print("TOTAIS GERAIS")
    print(f"{'=' * 60}")
    print(f"  Despesas:         {len(all_despesas)} registros")
    print(f"  Restos a Pagar:   {len(all_restos)} registros")
    print(f"  Despesas Orçadas: {len(all_orcadas)} registros")
    print(f"\n  Arquivos gerados:")
    print(f"    - despesas.json")
    print(f"    - despesas_restos.json")
    print(f"    - despesas_orcadas.json")
    print(f"    - despesas_consolidado.json")


if __name__ == "__main__":
    main()
