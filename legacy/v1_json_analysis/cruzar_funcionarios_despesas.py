"""
Script para cruzar dados de funcionários com despesas e restos a pagar.

Matching:
  1. CPF: Extrai os dígitos do meio do CPF mascarado do funcionário (***.XXX.XXX-**)
     e busca correspondência no CPF completo do credor nas despesas.
  2. Nome: Normaliza ambos os nomes (upper, sem acentos, trim) e compara.

Se qualquer match é encontrado, registra o funcionário com seus pagamentos.
"""
import json
import unicodedata
import re
import time
from datetime import datetime


def normalize_name(name: str) -> str:
    """Remove acentos, converte para uppercase e remove espaços extras."""
    if not name:
        return ""
    # Remove acentos
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Uppercase, remove espaços extras
    return " ".join(ascii_text.upper().split())


def extract_cpf_middle(masked_cpf: str) -> str:
    """
    Extrai os dígitos do meio de um CPF mascarado.
    Input:  ***.378.309-**
    Output: 378.309  (ou 378309 sem pontos)
    """
    if not masked_cpf:
        return ""
    # Remove asteriscos e traço
    # Formato: ***.XXX.XXX-**
    match = re.search(r"\*{3}\.(\d{3})\.(\d{3})-\*{2}", masked_cpf)
    if match:
        return match.group(1) + match.group(2)  # e.g. "378309"
    return ""


def extract_cpf_middle_from_full(full_cpf: str) -> str:
    """
    Extrai os mesmos dígitos do meio de um CPF completo.
    Input:  123.378.309-45
    Output: 378309
    """
    if not full_cpf:
        return ""
    # CPF completo: XXX.XXX.XXX-XX
    match = re.match(r"(\d{3})\.(\d{3})\.(\d{3})-(\d{2})", full_cpf)
    if match:
        return match.group(2) + match.group(3)  # middle 6 digits
    return ""


def is_cpf(doc: str) -> bool:
    """Verifica se o documento é um CPF (não CNPJ)."""
    if not doc:
        return False
    # CPF: XXX.XXX.XXX-XX (14 chars) / CNPJ tem barra
    return "/" not in doc and len(doc) <= 14 and "-" in doc


def parse_value(val) -> float:
    """Converte valor para float."""
    if not val:
        return 0.0
    try:
        return float(str(val))
    except ValueError:
        return 0.0


def main():
    print("=" * 60)
    print("Cruzamento Funcionários x Despesas")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # 1. Carregar dados
    print("\n1. Carregando dados...")

    with open("funcionarios_ordenados.json", "r", encoding="utf-8") as f:
        func_data = json.load(f)
    funcionarios = func_data["funcionarios"]
    print(f"   Funcionários: {len(funcionarios)}")

    with open("despesas.json", "r", encoding="utf-8") as f:
        desp_data = json.load(f)
    despesas = desp_data["registros"]
    print(f"   Despesas: {len(despesas)}")

    with open("despesas_restos.json", "r", encoding="utf-8") as f:
        rest_data = json.load(f)
    restos = rest_data["registros"]
    print(f"   Restos a Pagar: {len(restos)}")

    # 2. Indexar funcionários por CPF middle e nome normalizado
    print("\n2. Indexando funcionários...")

    func_by_cpf_mid = {}   # cpf_middle -> [func_index, ...]
    func_by_name = {}      # normalized_name -> [func_index, ...]

    for i, func in enumerate(funcionarios):
        # CPF middle
        cpf_mid = extract_cpf_middle(func.get("cpf", ""))
        if cpf_mid:
            func_by_cpf_mid.setdefault(cpf_mid, []).append(i)

        # Nome normalizado
        name_norm = normalize_name(func.get("nome", ""))
        if name_norm:
            func_by_name.setdefault(name_norm, []).append(i)

    print(f"   CPFs do meio únicos: {len(func_by_cpf_mid)}")
    print(f"   Nomes normalizados únicos: {len(func_by_name)}")

    # 3. Buscar matches em despesas
    print("\n3. Cruzando com despesas...")

    # Results dict: func_index -> { func_info, despesas: [], restos: [], match_type }
    matches = {}

    def add_match(func_idx, record, source, match_type):
        if func_idx not in matches:
            func = funcionarios[func_idx]
            matches[func_idx] = {
                "funcionario": {
                    "nome": func.get("nome"),
                    "cpf": func.get("cpf"),
                    "matricula": func.get("matricula"),
                    "cargo": func.get("cargo"),
                    "funcao": func.get("funcao"),
                    "salarioBase": func.get("salarioBase"),
                    "entidade": func.get("entidade"),
                    "centroCusto": func.get("centroCusto"),
                    "regime": func.get("regime"),
                    "situacao": func.get("situacao"),
                    "admissao": func.get("admissao"),
                },
                "despesas": [],
                "restos": [],
                "matchTypes": set(),
            }
        matches[func_idx]["matchTypes"].add(match_type)
        if source == "despesa":
            matches[func_idx]["despesas"].append(record)
        elif source == "resto":
            matches[func_idx]["restos"].append(record)

    # Search in despesas
    desp_matches = 0
    for rec in despesas:
        credor_cpf = rec.get("cpfCnpjCredor", "")
        credor_nome = rec.get("nomeCredor", "")

        # Try CPF match
        if is_cpf(credor_cpf):
            cpf_mid = extract_cpf_middle_from_full(credor_cpf)
            if cpf_mid and cpf_mid in func_by_cpf_mid:
                for idx in func_by_cpf_mid[cpf_mid]:
                    add_match(idx, rec, "despesa", "cpf")
                    desp_matches += 1
                continue  # CPF match takes priority

        # Try name match
        name_norm = normalize_name(credor_nome)
        if name_norm and name_norm in func_by_name:
            for idx in func_by_name[name_norm]:
                add_match(idx, rec, "despesa", "nome")
                desp_matches += 1

    print(f"   Matches em despesas: {desp_matches}")

    # Search in restos
    print("\n4. Cruzando com restos a pagar...")
    rest_matches = 0
    for rec in restos:
        credor_cpf = rec.get("cpfCnpjCredor", "")
        credor_nome = rec.get("nomeCredor", "")

        if is_cpf(credor_cpf):
            cpf_mid = extract_cpf_middle_from_full(credor_cpf)
            if cpf_mid and cpf_mid in func_by_cpf_mid:
                for idx in func_by_cpf_mid[cpf_mid]:
                    add_match(idx, rec, "resto", "cpf")
                    rest_matches += 1
                continue

        name_norm = normalize_name(credor_nome)
        if name_norm and name_norm in func_by_name:
            for idx in func_by_name[name_norm]:
                add_match(idx, rec, "resto", "nome")
                rest_matches += 1

    print(f"   Matches em restos: {rest_matches}")

    # 5. Consolidar e calcular totais
    print(f"\n5. Consolidando resultados...")
    print(f"   Funcionários com matches: {len(matches)}")

    results = []
    for func_idx, data in matches.items():
        # Calculate totals from despesas
        total_empenhado = sum(parse_value(d.get("valorEmpenhado", 0)) for d in data["despesas"])
        total_liquidado = sum(parse_value(d.get("valorLiquidado", 0)) for d in data["despesas"])
        total_pago_desp = sum(parse_value(d.get("valorPago", 0)) for d in data["despesas"])

        # Calculate totals from restos
        total_pago_restos = sum(parse_value(r.get("valorPago", 0)) for r in data["restos"])
        total_a_pagar = sum(parse_value(r.get("valorPagar", 0)) for r in data["restos"])

        results.append({
            "funcionario": data["funcionario"],
            "matchTypes": list(data["matchTypes"]),
            "resumo": {
                "totalDespesas": len(data["despesas"]),
                "totalRestos": len(data["restos"]),
                "despesas_valorEmpenhado": round(total_empenhado, 2),
                "despesas_valorLiquidado": round(total_liquidado, 2),
                "despesas_valorPago": round(total_pago_desp, 2),
                "restos_valorPago": round(total_pago_restos, 2),
                "restos_valorAPagar": round(total_a_pagar, 2),
                "totalGeralPago": round(total_pago_desp + total_pago_restos, 2),
            },
            "despesas": data["despesas"],
            "restos": data["restos"],
        })

    # Sort by total paid descending
    results.sort(key=lambda r: r["resumo"]["totalGeralPago"], reverse=True)

    # Save output
    output = {
        "dataConsulta": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "totalFuncionariosComPagamentos": len(results),
        "totalFuncionarios": len(funcionarios),
        "totalDespesasAnalisadas": len(despesas),
        "totalRestosAnalisados": len(restos),
        "funcionariosComPagamentos": results,
    }

    output_file = "funcionarios_com_despesas.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    import os
    size_kb = os.path.getsize(output_file) / 1024
    print(f"\n6. Salvo: {output_file} ({size_kb:.1f} KB)")

    # Print top results
    print(f"\n{'=' * 60}")
    print(f"TOP 20 FUNCIONÁRIOS COM MAIORES PAGAMENTOS")
    print(f"{'=' * 60}")
    for i, r in enumerate(results[:20], 1):
        func = r["funcionario"]
        resumo = r["resumo"]
        match_types = ", ".join(r["matchTypes"])
        print(f"\n  {i:2d}. {func['nome']}")
        print(f"      CPF: {func['cpf']} | Cargo: {func['cargo']}")
        print(f"      Salário Base: R$ {func['salarioBase']}")
        print(f"      Match: {match_types}")
        print(f"      Despesas: {resumo['totalDespesas']} registros | Pago: R$ {resumo['despesas_valorPago']:,.2f}")
        print(f"      Restos:   {resumo['totalRestos']} registros | Pago: R$ {resumo['restos_valorPago']:,.2f}")
        print(f"      TOTAL PAGO: R$ {resumo['totalGeralPago']:,.2f}")

    # Stats
    total_geral = sum(r["resumo"]["totalGeralPago"] for r in results)
    print(f"\n{'=' * 60}")
    print(f"ESTATÍSTICAS")
    print(f"{'=' * 60}")
    print(f"  Funcionários com pagamentos: {len(results)} de {len(funcionarios)}")
    print(f"  Total geral pago: R$ {total_geral:,.2f}")

    # Match type breakdown
    cpf_only = sum(1 for r in results if r["matchTypes"] == ["cpf"])
    name_only = sum(1 for r in results if r["matchTypes"] == ["nome"])
    both = sum(1 for r in results if len(r["matchTypes"]) > 1)
    print(f"  Matches por CPF: {cpf_only}")
    print(f"  Matches por nome: {name_only}")
    print(f"  Matches por ambos: {both}")


if __name__ == "__main__":
    main()
