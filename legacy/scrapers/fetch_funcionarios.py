"""
Script para buscar todos os funcionários da API de Transparência de Pessoal
de Tijucas (SC) com paginação e ordenar pelo maior salário.

Usa apenas stdlib (urllib) para evitar dependências externas.
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import ssl
import sys


BASE_URL = "https://tijucas.atende.net/api/transparencia-pessoal-funcionarios"
TIMEOUT = 120  # seconds per request


def parse_salary(salary_str: str) -> float:
    """
    Converte salário no formato brasileiro 'XX.XXX,XX' para float.
    Ex: '6.891,78' -> 6891.78
    """
    if not salary_str:
        return 0.0
    cleaned = salary_str.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def fetch_page(page: int, retries: int = 3) -> dict:
    """Busca uma página da API com retry."""
    ctx = ssl.create_default_context()
    params = urllib.parse.urlencode({"pagina": page, "tipoBusca": 1})
    url = f"{BASE_URL}?{params}"

    for attempt in range(retries):
        try:
            print(f"  Buscando página {page}...", end=" ", flush=True)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                registros = data.get("registros", [])
                print(f"OK ({len(registros)} registros)")
                return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 * (attempt + 1)
                print(f"Rate limit (tentativa {attempt+1}/{retries}), aguardando {wait}s...")
                time.sleep(wait)
            else:
                print(f"HTTP {e.code} (tentativa {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(3)
        except Exception as e:
            print(f"Erro (tentativa {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


def main():
    print("=" * 60)
    print("Busca de Funcionários - Tijucas Transparência")
    print("=" * 60)

    # Fetch first page
    print("\n1. Buscando primeira página para obter info de paginação...")
    first_page_data = fetch_page(1)
    if not first_page_data:
        print("ERRO: Não foi possível buscar a primeira página.")
        sys.exit(1)

    registros = first_page_data.get("registros", [])

    # Get pagination metadata
    total_paginas = first_page_data.get("totalPaginas")
    total_registros = first_page_data.get("totalRegistros")
    pagina_atual = first_page_data.get("paginaAtual")

    # Check inside first registro if not at root
    if total_paginas is None and registros:
        total_paginas = registros[0].get("totalPaginas")
        total_registros = registros[0].get("totalRegistros")
        pagina_atual = registros[0].get("paginaAtual")

    if total_paginas is None:
        print(f"  Chaves na resposta: {list(first_page_data.keys())}")
        if registros:
            print(f"  Chaves no primeiro registro: {list(registros[0].keys())}")

    print(f"\n  Página atual: {pagina_atual}")
    print(f"  Total de páginas: {total_paginas}")
    print(f"  Total de registros: {total_registros}")
    print(f"  Registros nesta página: {len(registros)}")

    all_funcionarios = list(registros)

    # Fetch remaining pages
    if total_paginas and total_paginas > 1:
        print(f"\n2. Buscando páginas restantes (2 a {total_paginas})...")
        for page in range(2, total_paginas + 1):
            data = fetch_page(page)
            if data:
                page_registros = data.get("registros", [])
                all_funcionarios.extend(page_registros)
            else:
                print(f"  AVISO: Falha ao buscar página {page}")
            time.sleep(1.5)

    print(f"\n3. Total de funcionários coletados: {len(all_funcionarios)}")

    # Remove pagination fields from each record if present
    pagination_keys = {"paginaAtual", "totalPaginas", "totalRegistros"}
    for func in all_funcionarios:
        for key in pagination_keys:
            func.pop(key, None)

    # Sort by salary (descending)
    print("\n4. Ordenando por salário (maior para menor)...")
    all_funcionarios.sort(
        key=lambda f: parse_salary(f.get("salarioBase", "0")), reverse=True
    )

    # Save to JSON
    output = {
        "totalRegistros": len(all_funcionarios),
        "ordenadoPor": "salarioBase (decrescente)",
        "dataConsulta": time.strftime("%d/%m/%Y %H:%M:%S"),
        "funcionarios": all_funcionarios,
    }

    output_file = "funcionarios_ordenados.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n5. Dados salvos em: {output_file}")

    # Print top 10
    print(f"\n{'=' * 60}")
    print("TOP 10 MAIORES SALÁRIOS")
    print(f"{'=' * 60}")
    for i, func in enumerate(all_funcionarios[:10], 1):
        nome = func.get("nome", "N/A")
        cargo = func.get("cargo", "N/A")
        salario = func.get("salarioBase", "N/A")
        print(f"  {i:2d}. {nome}")
        print(f"      Cargo: {cargo}")
        print(f"      Salário Base: R$ {salario}")
        print()

    # Print bottom 5
    print(f"\n{'=' * 60}")
    print("5 MENORES SALÁRIOS")
    print(f"{'=' * 60}")
    for i, func in enumerate(all_funcionarios[-5:], len(all_funcionarios) - 4):
        nome = func.get("nome", "N/A")
        cargo = func.get("cargo", "N/A")
        salario = func.get("salarioBase", "N/A")
        print(f"  {i:2d}. {nome}")
        print(f"      Cargo: {cargo}")
        print(f"      Salário Base: R$ {salario}")
        print()


if __name__ == "__main__":
    main()
