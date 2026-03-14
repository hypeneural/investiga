"""
Análise de Indícios de Fraudes - Prefeitura de Tijucas (SC)
Dados Públicos do Portal da Transparência

Análises realizadas:
  1. NEPOTISMO: Agrupamento de funcionários por sobrenome
  2. FUNCIONÁRIO-CREDOR: Funcionários que recebem pagamentos como credores
  3. CPF DUPLICADO: Múltiplas matrículas com mesmo CPF
  4. CONCENTRAÇÃO DE PAGAMENTOS: Credores que recebem valores desproporcionais
  5. OUTLIERS SALARIAIS: Salários fora do padrão para o mesmo cargo
  6. RESTOS A PAGAR SUSPEITOS: Valores altos pendentes por credor
  7. ACÚMULO DE CARGOS: Funcionários com múltiplas matrículas ativas
"""
import json
import unicodedata
import re
import os
import statistics
from datetime import datetime
from collections import defaultdict, Counter


# ──────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    """Remove acentos, uppercase, remove espaços extras."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_text.upper().split())


def parse_salary(s: str) -> float:
    """'6.891,78' -> 6891.78"""
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def parse_value(v) -> float:
    if not v:
        return 0.0
    try:
        return float(str(v))
    except ValueError:
        return 0.0


def extract_cpf_mid(masked: str) -> str:
    """\***.378.309-** -> 378309"""
    m = re.search(r"\*{3}\.(\d{3})\.(\d{3})-\*{2}", masked or "")
    return m.group(1) + m.group(2) if m else ""


def extract_cpf_mid_full(full: str) -> str:
    """123.378.309-45 -> 378309"""
    m = re.match(r"\d{3}\.(\d{3})\.(\d{3})-\d{2}", full or "")
    return m.group(1) + m.group(2) if m else ""


def is_cpf(doc: str) -> bool:
    return bool(doc) and "/" not in doc and len(doc) <= 14 and "-" in doc


def get_sobrenome(nome: str) -> str:
    """Retorna o último sobrenome."""
    parts = normalize(nome).split()
    if len(parts) >= 2:
        return parts[-1]
    return parts[0] if parts else ""


def get_sobrenomes(nome: str) -> list:
    """Retorna todos os sobrenomes (exceto primeiro nome e preposições)."""
    parts = normalize(nome).split()
    preposicoes = {"DE", "DA", "DO", "DOS", "DAS", "E"}
    if len(parts) <= 1:
        return []
    return [p for p in parts[1:] if p not in preposicoes]


# ──────────────────────────────────────────────────────────
# CARREGAR DADOS
# ──────────────────────────────────────────────────────────

def load_data():
    print("Carregando dados...")
    with open("funcionarios_ordenados.json", "r", encoding="utf-8") as f:
        funcs = json.load(f)["funcionarios"]
    with open("despesas.json", "r", encoding="utf-8") as f:
        despesas = json.load(f)["registros"]
    with open("despesas_restos.json", "r", encoding="utf-8") as f:
        restos = json.load(f)["registros"]
    print(f"  Funcionários: {len(funcs)}")
    print(f"  Despesas: {len(despesas)}")
    print(f"  Restos a pagar: {len(restos)}")
    return funcs, despesas, restos


# ──────────────────────────────────────────────────────────
# ANÁLISE 1: NEPOTISMO — Sobrenomes em comum
# ──────────────────────────────────────────────────────────

def analise_nepotismo(funcs):
    print("\n" + "=" * 60)
    print("ANÁLISE 1: NEPOTISMO — Sobrenomes em Comum")
    print("=" * 60)

    sobrenome_groups = defaultdict(list)
    for func in funcs:
        ultimo = get_sobrenome(func.get("nome", ""))
        if ultimo and len(ultimo) > 2:  # Ignora sobrenomes muito curtos
            sobrenome_groups[ultimo].append(func)

    # Filtrar apenas grupos com 3+ funcionários (famílias grandes)
    familias = {
        sob: members
        for sob, members in sobrenome_groups.items()
        if len(members) >= 3
    }

    # Ordenar por quantidade (maior primeiro)
    familias_sorted = sorted(familias.items(), key=lambda x: len(x[1]), reverse=True)

    results = []
    for sob, members in familias_sorted:
        centros_custo = set(m.get("centroCusto", "") for m in members)
        cargos = Counter(m.get("cargo", "") for m in members)
        salarios = [parse_salary(m.get("salarioBase", "0")) for m in members]
        total_salarios = sum(salarios)

        entry = {
            "sobrenome": sob,
            "qtdFuncionarios": len(members),
            "totalSalarios": round(total_salarios, 2),
            "centrosCusto": list(centros_custo),
            "mesmoSetor": len(centros_custo) == 1,
            "cargos": dict(cargos),
            "funcionarios": [
                {
                    "nome": m.get("nome"),
                    "cpf": m.get("cpf"),
                    "cargo": m.get("cargo"),
                    "salarioBase": m.get("salarioBase"),
                    "centroCusto": m.get("centroCusto"),
                    "regime": m.get("regime"),
                    "situacao": m.get("situacao"),
                }
                for m in members
            ],
        }

        # Flag: suspeito se muitos no mesmo setor
        if len(centros_custo) == 1 and len(members) >= 3:
            entry["alerta"] = "MESMO SETOR - Possível nepotismo"

        results.append(entry)

    print(f"  Sobrenomes com 3+ funcionários: {len(results)}")
    top5 = results[:5]
    for r in top5:
        alert = f" ⚠️  {r['alerta']}" if "alerta" in r else ""
        print(f"  • {r['sobrenome']}: {r['qtdFuncionarios']} funcionários"
              f" | R$ {r['totalSalarios']:,.2f}{alert}")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 2: FUNCIONÁRIO-CREDOR — duplo vínculo
# ──────────────────────────────────────────────────────────

def analise_funcionario_credor(funcs, despesas, restos):
    print("\n" + "=" * 60)
    print("ANÁLISE 2: FUNCIONÁRIOS COMO CREDORES DE DESPESAS")
    print("=" * 60)

    # Index funcionários por CPF middle
    func_by_cpf = defaultdict(list)
    for func in funcs:
        mid = extract_cpf_mid(func.get("cpf", ""))
        if mid:
            func_by_cpf[mid].append(func)

    # Buscar matches em despesas + restos
    credor_pagtos = defaultdict(lambda: {"despesas": [], "restos": []})

    for rec in despesas:
        cpf = rec.get("cpfCnpjCredor", "")
        if is_cpf(cpf):
            mid = extract_cpf_mid_full(cpf)
            if mid and mid in func_by_cpf:
                credor_pagtos[mid]["despesas"].append(rec)

    for rec in restos:
        cpf = rec.get("cpfCnpjCredor", "")
        if is_cpf(cpf):
            mid = extract_cpf_mid_full(cpf)
            if mid and mid in func_by_cpf:
                credor_pagtos[mid]["restos"].append(rec)

    results = []
    for cpf_mid, pagtos in credor_pagtos.items():
        func_list = func_by_cpf[cpf_mid]
        func = func_list[0]  # Use first match

        total_desp_pago = sum(parse_value(d.get("valorPago", 0)) for d in pagtos["despesas"])
        total_rest_pago = sum(parse_value(r.get("valorPago", 0)) for r in pagtos["restos"])
        total_pago = total_desp_pago + total_rest_pago
        salario = parse_salary(func.get("salarioBase", "0"))
        salario_anual = salario * 13  # 13º salário

        entry = {
            "nome": func.get("nome"),
            "cpf": func.get("cpf"),
            "cargo": func.get("cargo"),
            "salarioBase": func.get("salarioBase"),
            "salarioAnualEstimado": round(salario_anual, 2),
            "totalPagoDespesas": round(total_desp_pago, 2),
            "totalPagoRestos": round(total_rest_pago, 2),
            "totalPago": round(total_pago, 2),
            "ratioPagoVsSalario": round(total_pago / salario_anual, 2) if salario_anual > 0 else 0,
            "qtdDespesas": len(pagtos["despesas"]),
            "qtdRestos": len(pagtos["restos"]),
            "alertas": [],
        }

        # Flags
        if total_pago > salario_anual * 2:
            entry["alertas"].append(f"PAGAMENTO MUITO ACIMA DO SALÁRIO: {entry['ratioPagoVsSalario']}x")
        if total_pago > 50000:
            entry["alertas"].append(f"PAGAMENTO ALTO: R$ {total_pago:,.2f}")
        if func.get("situacao") == "Trabalhando" and total_pago > salario_anual:
            entry["alertas"].append("FUNCIONÁRIO ATIVO recebendo pagamentos adicionais")

        if entry["alertas"]:
            results.append(entry)

    results.sort(key=lambda x: x["totalPago"], reverse=True)

    print(f"  Funcionários-credores com alertas: {len(results)}")
    for r in results[:5]:
        print(f"  ⚠️  {r['nome']} | Cargo: {r['cargo']}")
        print(f"      Salário: R$ {r['salarioBase']} | Pago como credor: R$ {r['totalPago']:,.2f}")
        for a in r["alertas"]:
            print(f"      → {a}")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 3: CPFs DUPLICADOS / MÚLTIPLAS MATRÍCULAS
# ──────────────────────────────────────────────────────────

def analise_cpf_duplicado(funcs):
    print("\n" + "=" * 60)
    print("ANÁLISE 3: CPFs COM MÚLTIPLAS MATRÍCULAS")
    print("=" * 60)

    cpf_groups = defaultdict(list)
    for func in funcs:
        mid = extract_cpf_mid(func.get("cpf", ""))
        if mid:
            cpf_groups[mid].append(func)

    duplicados = {
        mid: members
        for mid, members in cpf_groups.items()
        if len(members) >= 2
    }

    results = []
    for mid, members in sorted(duplicados.items(), key=lambda x: len(x[1]), reverse=True):
        salarios = [parse_salary(m.get("salarioBase", "0")) for m in members]
        total = sum(salarios)
        situacoes = [m.get("situacao", "") for m in members]
        ativos = sum(1 for s in situacoes if s == "Trabalhando")

        entry = {
            "cpfMeio": f"***.{mid[:3]}.{mid[3:]}-**",
            "qtdMatriculas": len(members),
            "totalSalarios": round(total, 2),
            "ativosSimultaneos": ativos,
            "alertas": [],
            "matriculas": [
                {
                    "nome": m.get("nome"),
                    "matricula": m.get("matricula"),
                    "cargo": m.get("cargo"),
                    "salarioBase": m.get("salarioBase"),
                    "situacao": m.get("situacao"),
                    "regime": m.get("regime"),
                    "centroCusto": m.get("centroCusto"),
                }
                for m in members
            ],
        }

        if ativos >= 2:
            entry["alertas"].append(f"ACÚMULO DE CARGOS: {ativos} vínculos ativos simultâneos")
        if total > 30000:
            entry["alertas"].append(f"SOMA SALARIAL ALTA: R$ {total:,.2f}")

        results.append(entry)

    results.sort(key=lambda x: x["totalSalarios"], reverse=True)

    alertados = [r for r in results if r["alertas"]]
    print(f"  CPFs com múltiplas matrículas: {len(results)}")
    print(f"  Com alertas: {len(alertados)}")
    for r in alertados[:5]:
        print(f"  ⚠️  {r['cpfMeio']} — {r['qtdMatriculas']} matrículas | R$ {r['totalSalarios']:,.2f}")
        for a in r["alertas"]:
            print(f"      → {a}")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 4: CONCENTRAÇÃO DE PAGAMENTOS POR CREDOR
# ──────────────────────────────────────────────────────────

def analise_concentracao_pagamentos(despesas):
    print("\n" + "=" * 60)
    print("ANÁLISE 4: CONCENTRAÇÃO DE PAGAMENTOS POR CREDOR (CPF)")
    print("=" * 60)

    credor_totais = defaultdict(lambda: {
        "nome": "", "cpf": "", "totalEmpenhado": 0, "totalPago": 0,
        "qtdRegistros": 0, "orgaos": set(), "fontes": set()
    })

    for rec in despesas:
        cpf = rec.get("cpfCnpjCredor", "")
        if not is_cpf(cpf):
            continue

        c = credor_totais[cpf]
        c["nome"] = rec.get("nomeCredor", "")
        c["cpf"] = cpf
        c["totalEmpenhado"] += parse_value(rec.get("valorEmpenhado", 0))
        c["totalPago"] += parse_value(rec.get("valorPago", 0))
        c["qtdRegistros"] += 1
        c["orgaos"].add(rec.get("orgaoDescricao", ""))
        c["fontes"].add(rec.get("fonteRecursoDescricao", ""))

    results = []
    for cpf, data in credor_totais.items():
        if data["totalPago"] >= 100000:  # Credores PF com +100k
            results.append({
                "nome": data["nome"],
                "cpf": data["cpf"],
                "totalEmpenhado": round(data["totalEmpenhado"], 2),
                "totalPago": round(data["totalPago"], 2),
                "qtdRegistros": data["qtdRegistros"],
                "orgaos": list(data["orgaos"]),
                "fontesRecurso": list(data["fontes"]),
                "alertas": [],
            })

    for r in results:
        if r["qtdRegistros"] >= 10:
            r["alertas"].append(f"MUITOS PAGAMENTOS: {r['qtdRegistros']} registros")
        if r["totalPago"] >= 500000:
            r["alertas"].append(f"VALOR MUITO ALTO para PF: R$ {r['totalPago']:,.2f}")
        if len(r["orgaos"]) >= 3:
            r["alertas"].append(f"RECEBE DE MÚLTIPLOS ÓRGÃOS: {len(r['orgaos'])}")

    results.sort(key=lambda x: x["totalPago"], reverse=True)

    print(f"  Credores PF com +R$100k em pagamentos: {len(results)}")
    for r in results[:5]:
        alertas = " | ".join(r["alertas"]) if r["alertas"] else ""
        print(f"  • {r['nome']} ({r['cpf']})")
        print(f"    Pago: R$ {r['totalPago']:,.2f} em {r['qtdRegistros']} registros")
        if alertas:
            print(f"    ⚠️  {alertas}")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 5: OUTLIERS SALARIAIS POR CARGO
# ──────────────────────────────────────────────────────────

def analise_outliers_salariais(funcs):
    print("\n" + "=" * 60)
    print("ANÁLISE 5: OUTLIERS SALARIAIS POR CARGO")
    print("=" * 60)

    cargo_salarios = defaultdict(list)
    for func in funcs:
        cargo = func.get("cargo", "DESCONHECIDO")
        salario = parse_salary(func.get("salarioBase", "0"))
        if salario > 0:
            cargo_salarios[cargo].append((func, salario))

    results = []
    for cargo, members in cargo_salarios.items():
        if len(members) < 3:
            continue

        salarios = [s for _, s in members]
        media = statistics.mean(salarios)
        try:
            desvio = statistics.stdev(salarios)
        except statistics.StatisticsError:
            desvio = 0

        if desvio == 0:
            continue

        outliers = []
        for func, sal in members:
            z_score = (sal - media) / desvio if desvio > 0 else 0
            if abs(z_score) > 2:  # 2 desvios padrão
                outliers.append({
                    "nome": func.get("nome"),
                    "cpf": func.get("cpf"),
                    "salarioBase": func.get("salarioBase"),
                    "salarioFloat": round(sal, 2),
                    "zScore": round(z_score, 2),
                    "regime": func.get("regime"),
                    "centroCusto": func.get("centroCusto"),
                    "nivel": func.get("nivel"),
                })

        if outliers:
            results.append({
                "cargo": cargo,
                "qtdFuncionarios": len(members),
                "mediaSalarial": round(media, 2),
                "desvioPadrao": round(desvio, 2),
                "menorSalario": round(min(salarios), 2),
                "maiorSalario": round(max(salarios), 2),
                "outliers": outliers,
            })

    results.sort(key=lambda x: max(o["zScore"] for o in x["outliers"]), reverse=True)

    print(f"  Cargos com outliers salariais: {len(results)}")
    for r in results[:5]:
        print(f"  • {r['cargo']} (média R$ {r['mediaSalarial']:,.2f})")
        for o in r["outliers"][:2]:
            print(f"    ⚠️  {o['nome']}: R$ {o['salarioFloat']:,.2f} (Z={o['zScore']})")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 6: RESTOS A PAGAR SUSPEITOS
# ──────────────────────────────────────────────────────────

def analise_restos_suspeitos(restos):
    print("\n" + "=" * 60)
    print("ANÁLISE 6: RESTOS A PAGAR SUSPEITOS (PF)")
    print("=" * 60)

    credor_restos = defaultdict(lambda: {
        "nome": "", "cpf": "", "totalAPagar": 0, "totalPago": 0,
        "totalEmpenhado": 0, "qtd": 0
    })

    for rec in restos:
        cpf = rec.get("cpfCnpjCredor", "")
        if not is_cpf(cpf):
            continue
        c = credor_restos[cpf]
        c["nome"] = rec.get("nomeCredor", "")
        c["cpf"] = cpf
        c["totalAPagar"] += parse_value(rec.get("valorPagar", 0))
        c["totalPago"] += parse_value(rec.get("valorPago", 0))
        c["totalEmpenhado"] += parse_value(rec.get("valorEmpenhado", 0))
        c["qtd"] += 1

    results = []
    for cpf, data in credor_restos.items():
        if data["totalAPagar"] >= 10000 or data["totalPago"] >= 50000:
            entry = {
                "nome": data["nome"],
                "cpf": data["cpf"],
                "totalAPagar": round(data["totalAPagar"], 2),
                "totalPago": round(data["totalPago"], 2),
                "totalEmpenhado": round(data["totalEmpenhado"], 2),
                "qtdRegistros": data["qtd"],
                "alertas": [],
            }
            if data["totalAPagar"] >= 50000:
                entry["alertas"].append(f"VALOR ALTO A PAGAR: R$ {data['totalAPagar']:,.2f}")
            if data["totalPago"] >= 100000:
                entry["alertas"].append(f"VALOR ALTO JÁ PAGO: R$ {data['totalPago']:,.2f}")
            results.append(entry)

    results.sort(key=lambda x: x["totalAPagar"], reverse=True)

    print(f"  Credores PF com restos relevantes: {len(results)}")
    for r in results[:5]:
        print(f"  • {r['nome']} ({r['cpf']})")
        print(f"    A Pagar: R$ {r['totalAPagar']:,.2f} | Pago: R$ {r['totalPago']:,.2f}")
        for a in r["alertas"]:
            print(f"    ⚠️  {a}")

    return results


# ──────────────────────────────────────────────────────────
# ANÁLISE 7: PARENTESCO NO MESMO SETOR (últimos 2 sobrenomes)
# ──────────────────────────────────────────────────────────

def analise_parentesco_setor(funcs):
    print("\n" + "=" * 60)
    print("ANÁLISE 7: POSSÍVEL PARENTESCO NO MESMO SETOR")
    print("=" * 60)

    # Agrupar por centro de custo
    setor_funcs = defaultdict(list)
    for func in funcs:
        cc = func.get("centroCusto", "")
        if cc:
            setor_funcs[cc].append(func)

    results = []
    for setor, members in setor_funcs.items():
        if len(members) < 2:
            continue

        # Checar sobrenomes em comum dentro do setor
        sobrenome_map = defaultdict(list)
        for m in members:
            sobrenomes = get_sobrenomes(m.get("nome", ""))
            for sob in sobrenomes:
                if len(sob) > 2:  # Ignora sobrenomes muito curtos
                    sobrenome_map[sob].append(m)

        for sob, group in sobrenome_map.items():
            if len(group) >= 2:
                # Verificar se não são a mesma pessoa (CPF diferente)
                cpfs = set(m.get("cpf", "") for m in group)
                if len(cpfs) >= 2:  # Pelo menos 2 pessoas diferentes
                    entry = {
                        "centroCusto": setor,
                        "sobrenomeComum": sob,
                        "qtdPessoas": len(cpfs),
                        "funcionarios": [
                            {
                                "nome": m.get("nome"),
                                "cpf": m.get("cpf"),
                                "cargo": m.get("cargo"),
                                "salarioBase": m.get("salarioBase"),
                            }
                            for m in group
                        ],
                    }
                    results.append(entry)

    # Dedup (some pairs appear via different shared surnames)
    seen = set()
    deduped = []
    for r in results:
        key = (r["centroCusto"], frozenset(f["cpf"] for f in r["funcionarios"]))
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    results = sorted(deduped, key=lambda x: x["qtdPessoas"], reverse=True)

    print(f"  Grupos com possível parentesco no mesmo setor: {len(results)}")
    for r in results[:10]:
        nomes = ", ".join(f["nome"] for f in r["funcionarios"])
        print(f"  • [{r['centroCusto']}] Sobrenome '{r['sobrenomeComum']}': {nomes}")

    return results


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ANÁLISE DE INDÍCIOS DE FRAUDES")
    print("Prefeitura de Tijucas (SC) - Dados Públicos")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    funcs, despesas, restos = load_data()

    # Executar todas as análises
    r1 = analise_nepotismo(funcs)
    r2 = analise_funcionario_credor(funcs, despesas, restos)
    r3 = analise_cpf_duplicado(funcs)
    r4 = analise_concentracao_pagamentos(despesas)
    r5 = analise_outliers_salariais(funcs)
    r6 = analise_restos_suspeitos(restos)
    r7 = analise_parentesco_setor(funcs)

    # Consolidar resultado
    resultado = {
        "titulo": "Análise de Indícios de Fraudes - Prefeitura de Tijucas (SC)",
        "dataAnalise": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "fonteDados": "Portal da Transparência - Dados Abertos",
        "resumo": {
            "totalFuncionarios": len(funcs),
            "totalDespesas": len(despesas),
            "totalRestos": len(restos),
            "sobrenomesComMuitosFuncionarios": len(r1),
            "funcionariosCredoresComAlertas": len(r2),
            "cpfsDuplicados": len(r3),
            "credoresPFAltosValores": len(r4),
            "cargosComOutliersSalariais": len(r5),
            "credoresComRestosSuspeitos": len(r6),
            "gruposParentescoMesmoSetor": len(r7),
        },
        "analise1_nepotismo": r1,
        "analise2_funcionario_credor": r2,
        "analise3_cpf_duplicados": r3,
        "analise4_concentracao_pagamentos": r4,
        "analise5_outliers_salariais": r5,
        "analise6_restos_suspeitos": r6,
        "analise7_parentesco_setor": r7,
    }

    output_file = "analise_fraudes.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(output_file) / 1024
    print(f"\n{'=' * 60}")
    print(f"RESULTADO SALVO: {output_file} ({size_kb:.1f} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
