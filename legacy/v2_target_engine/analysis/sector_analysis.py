from typing import List, Dict, Any
from collections import defaultdict
from .utils import parse_salary, parse_value, extract_human_name_from_credor, is_cpf
from .loaders import SECTOR_OWNERSHIP

# Blacklist of internal/public entities to exclude from concentration metrics
INTERNAL_CREDITORS = [
    "MUNICIPIO DE TIJUCAS",
    "FUNDO MUNICIPAL",
    "CAMARA MUNICIPAL",
    "INSS",
    "FGTS",
    "RECEITA FEDERAL",
    "FAZENDA",
    "PREVIDENCIA",
    "PREVISERTI",
    "CAIXA ECONOMICA",
    "BANCO DO BRASIL",
    "PASEP",
    "MINISTERIO"
]

def is_internal_creditor(name: str) -> bool:
    if not name:
        return False
    # Remove accents/special chars manually or just do simple check
    name_upper = name.upper().replace('Á', 'A').replace('Â', 'A').replace('Ã', 'A').replace('É', 'E').replace('Ê', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ô', 'O').replace('Õ', 'O').replace('Ú', 'U').replace('Ç', 'C')
    for ic in INTERNAL_CREDITORS:
        if ic in name_upper:
            return True
    return False

class SectorAnalyzer:
    def __init__(self, funcionarios: list, despesas: list, restos: list):
        self.funcs = funcionarios
        self.despesas = despesas
        self.restos = restos
        
    def analyze_sector(self, centro_custo: str) -> dict:
        """
        Analyzes the target's sector (centroCusto).
        Returns stats about commission vs effective employees, salary distribution, etc.
        """
        if not centro_custo:
            return {}
            
        sector_funcs = [f for f in self.funcs if f.get("centroCusto") == centro_custo]
        
        if not sector_funcs:
            return {}
            
        stats = {
            "centroCusto": centro_custo,
            "qtdFuncionarios": len(sector_funcs),
            "comissionados": 0,
            "efetivos": 0,
            "outros": 0,
            "totalSalarios": 0.0,
            "cargosDist": defaultdict(int)
        }
        
        for f in sector_funcs:
            regime = (f.get("regime") or "").upper()
            if "COMISSION" in regime or "CONFIAN" in regime or "CC" in regime:
                stats["comissionados"] = int(stats.get("comissionados", 0)) + 1
            elif "EFETIVO" in regime or "CONCURSO" in regime:
                stats["efetivos"] = int(stats.get("efetivos", 0)) + 1
            else:
                stats["outros"] = int(stats.get("outros", 0)) + 1
                
            
            stats["totalSalarios"] = float(stats.get("totalSalarios", 0.0)) + parse_salary(f.get("salarioBase", ""))
            
            cargos_dict = stats.get("cargosDist", defaultdict(int))
            if isinstance(cargos_dict, dict):
                cargos_dict[f.get("cargo", "DESCONHECIDO")] = int(cargos_dict.get(f.get("cargo", "DESCONHECIDO"), 0)) + 1
                stats["cargosDist"] = cargos_dict
            
        stats["cargosDist"] = dict(stats.get("cargosDist", {}))
        stats["totalSalarios"] = float(round(float(stats.get("totalSalarios", 0.0)), 2))
        
        # New: Hiring waves (Ondas de Nomeação)
        # Group by admission month (MM/YYYY)
        admissoes_por_mes = defaultdict(list)
        for f in sector_funcs:
            data_adm = f.get("admissao", "")
            if data_adm and len(data_adm.split("/")) >= 3:
                parts = data_adm.split("/")
                mes_ano = f"{parts[1]}/{parts[2]}"
                admissoes_por_mes[mes_ano].append(f.get("nome", ""))
                
        # Filter for months with 3 or more hirings in this sector
        ondas = []
        for mes, nomes in admissoes_por_mes.items():
            if len(nomes) >= 4:
                ondas.append({
                    "mes": mes,
                    "quantidade": len(nomes),
                    "nomes": nomes[:5] # Sample of up to 5 names
                })
        ondas.sort(key=lambda x: x["quantidade"], reverse=True)
        stats["ondasNomeacao"] = ondas[:5]

        return stats

    def analyze_sector_financials(self, target_name: str) -> dict:
        """
        Analyzes the financial aspects (creditors, payments, concentration, fractioning) 
        of the organs/units controlled by the given target name.
        """
        ownership = SECTOR_OWNERSHIP.get(target_name)
        if not ownership or (not ownership["orgaos"] and not ownership["unidades"]):
            return {}
            
        target_orgaos = set(o.lower() for o in ownership["orgaos"])
        target_unidades = set(u.lower() for u in ownership["unidades"])
        
        # Filter all payments that happened in these organs/units
        sector_despesas = []
        for p in self.despesas:
            o_desc = p.get("orgaoDescricao", "").lower()
            u_desc = p.get("unidadeDescricao", "").lower()
            if any(to in o_desc for to in target_orgaos) or any(tu in u_desc for tu in target_unidades):
                sector_despesas.append(p)
                
        sector_restos = []
        for p in self.restos:
            o_desc = p.get("orgaoDescricao", "").lower()
            u_desc = p.get("unidadeDescricao", "").lower()
            if any(to in o_desc for to in target_orgaos) or any(tu in u_desc for tu in target_unidades):
                sector_restos.append(p)
                
        if not sector_despesas and not sector_restos:
            return {}

        stats = {
            "totalPagoNoSetorExercicio": 0.0,
            "totalPagoNoSetorRestos": 0.0,
            "totalEmpenhadoControle": 0.0,
            "totalAnuladoControle": 0.0,
            "totalLiquidadoControle": 0.0,
            "totalRetidoControle": 0.0,
            "topCredoresPFPrivados": [],
            "topCredoresCNPJPrivados": [],
            "alertasFracionamento": [],
            "alertasAnulacao": []
        }
        
        credor_totals = defaultdict(float)
        credor_is_pf = {}
        credor_human_names = {}
        
        # Tracking fractioning: by Creditor -> Month -> list of values
        # e.g fractioning_tracker["123.456..."]["05/2023"] = [7000, 7500, 8000]
        fractioning_tracker = defaultdict(lambda: defaultdict(list))
        
        def process_payments(payments_list, is_restos=False):
            for p in payments_list:
                # V4.1.1a: Use parse_value() for despesa amounts (US format), not parse_salary() (BR format)
                valor = parse_value(p.get("valorPago", ""))
                v_empenho = parse_value(p.get("valorEmpenhado", ""))
                v_anulado = parse_value(p.get("valorAnulado", p.get("valorProcessadoCancelado", p.get("valorNaoProcessadoCancelado", ""))))
                v_liquidado = parse_value(p.get("valorLiquidado", p.get("valorNaoProcessadoLiquidado", "")))
                v_retido = parse_value(p.get("valorRetido", ""))
                
                cpf_cnpj = p.get("cpfCnpjCredor", "")
                nome = p.get("nomeCredor", "")
                
                if is_internal_creditor(nome):
                    continue
                    
                stats["totalEmpenhadoControle"] = float(stats.get("totalEmpenhadoControle", 0.0)) + v_empenho
                stats["totalAnuladoControle"] = float(stats.get("totalAnuladoControle", 0.0)) + v_anulado
                stats["totalLiquidadoControle"] = float(stats.get("totalLiquidadoControle", 0.0)) + v_liquidado
                stats["totalRetidoControle"] = float(stats.get("totalRetidoControle", 0.0)) + v_retido

                if valor <= 0:
                    continue
                    
                if is_restos:
                    stats["totalPagoNoSetorRestos"] = float(stats.get("totalPagoNoSetorRestos", 0.0)) + valor
                else:
                    stats["totalPagoNoSetorExercicio"] = float(stats.get("totalPagoNoSetorExercicio", 0.0)) + valor
                    
                credor_totals[cpf_cnpj] += valor
                credor_is_pf[cpf_cnpj] = is_cpf(cpf_cnpj)
                credor_human_names[cpf_cnpj] = extract_human_name_from_credor(nome)
                
                # Extract month/year for fractioning analysis
                # V4.2: Hotfix 2 - Use _ano and _mes ideally, fallback to textual dates
                ano_str = p.get("_ano", "")
                mes_str = p.get("_mes", "")
                
                if ano_str and mes_str:
                    month_key = f"{mes_str:0>2}/{ano_str}"
                    fractioning_tracker[cpf_cnpj][month_key].append(valor)
                else:
                    date_str = p.get("dataPagamento") or p.get("dataLiquidacao") or p.get("dataEmpenho") or ""
                    parts = date_str.split("/")
                    if len(parts) >= 3:
                        month_key = f"{parts[1]}/{parts[2]}"
                        fractioning_tracker[cpf_cnpj][month_key].append(valor)
                    
        process_payments(sector_despesas, is_restos=False)
        process_payments(sector_restos, is_restos=True)
                
        stats["totalPagoNoSetorExercicio"] = float(round(float(stats.get("totalPagoNoSetorExercicio", 0.0)), 2))
        stats["totalPagoNoSetorRestos"] = float(round(float(stats.get("totalPagoNoSetorRestos", 0.0)), 2))
        stats["totalEmpenhadoControle"] = float(round(float(stats.get("totalEmpenhadoControle", 0.0)), 2))
        stats["totalAnuladoControle"] = float(round(float(stats.get("totalAnuladoControle", 0.0)), 2))
        stats["totalLiquidadoControle"] = float(round(float(stats.get("totalLiquidadoControle", 0.0)), 2))
        stats["totalRetidoControle"] = float(round(float(stats.get("totalRetidoControle", 0.0)), 2))
        
        total_privado = float(stats.get("totalPagoNoSetorExercicio", 0.0)) + float(stats.get("totalPagoNoSetorRestos", 0.0))
        
        # Sort creditors
        sorted_creds = sorted(credor_totals.items(), key=lambda x: x[1], reverse=True)
        
        pf_count = 0
        cnpj_count = 0
        for cpf_cnpj, total in sorted_creds:
            cred_info = {
                "documento": cpf_cnpj,
                "nomeExtraido": credor_human_names[cpf_cnpj],
                "totalRecebido": round(total, 2),
                "percOrcamento": round((total / total_privado) * 100, 2) if total_privado > 0 else 0.0
            }
            if credor_is_pf.get(cpf_cnpj, False):
                if pf_count < 10:
                    stats["topCredoresPFPrivados"].append(cred_info)
                    pf_count += 1
            else:
                if cnpj_count < 10:
                    stats["topCredoresCNPJPrivados"].append(cred_info)
                    cnpj_count += 1

        # Analyze fractioning
        for cpf_cnpj, months in fractioning_tracker.items():
            for month, values in months.items():
                qtd = len(values)
                soma_mes = sum(values)
                
                # Trilha 5: Fracionamento e Dispensas Suspeitas (V4.2 - Fracionamento Avançado)
                classificacao = None
                
                # Check for value clusters / proximity (identical or very similar slices)
                proximidade = False
                variance_pct = 1.0
                if qtd >= 2:
                    val_max = max(values)
                    val_min = min(values)
                    if soma_mes > 0:
                        variance_pct = (val_max - val_min) / val_max if val_max > 0 else 0
                    if variance_pct <= 0.05: # Less than 5% variance between slices
                        proximidade = True
                
                # V4.2 limits and rules
                if (qtd >= 3 and soma_mes > 15000) or (qtd >= 2 and soma_mes > 15000 and proximidade):
                    classificacao = "FORTE"
                elif (qtd >= 2 and soma_mes > 30000) or (qtd >= 3 and soma_mes >= 8000) or (qtd >= 2 and soma_mes > 5000 and proximidade):
                    classificacao = "MEDIO"
                    
                if classificacao:
                    stats["alertasFracionamento"].append({
                        "credorNome": credor_human_names[cpf_cnpj],
                        "documento": cpf_cnpj,
                        "mes": month,
                        "qtdPagamentos": qtd,
                        "somaNoMes": round(soma_mes, 2),
                        "valores": [round(v, 2) for v in values],
                        "classificacao": classificacao
                    })
                        
        # Sort fractioning alerts by severity (FORTE first) then sum
        stats["alertasFracionamento"] = sorted(
            [a for a in stats["alertasFracionamento"] if isinstance(a, dict)],
            key=lambda x: (1 if x.get("classificacao") == "FORTE" else 2, -float(x.get("somaNoMes", 0)))
        )
        # Trilha 6: Desistências / Anulações Ocultas
        # Alert if anulado > 30% of empenhado or retido > 20% of liquidado (suspicious behavior in sector)
        total_emp = stats["totalEmpenhadoControle"]
        total_anu = stats["totalAnuladoControle"]
        total_liq = stats["totalLiquidadoControle"]
        total_ret = stats["totalRetidoControle"]
        
        if total_emp > 0 and (total_anu / total_emp) >= 0.3:
            stats["alertasAnulacao"].append({
                "tipo": "ANULACAO_ATIPICA_SETOR",
                "motivo": f"Anulações representam {round((total_anu/total_emp)*100, 1)}% do total empenhado do setor no período",
                "valorAnulado": total_anu,
                "valorEmpenhado": total_emp
            })
            
        if total_liq > 0 and (total_ret / total_liq) >= 0.2:
            stats["alertasAnulacao"].append({
                "tipo": "RETENCAO_ATIPICA_SETOR",
                "motivo": f"Retenções representam {round((total_ret/total_liq)*100, 1)}% do total liquidado do setor no período",
                "valorRetido": total_ret,
                "valorLiquidado": total_liq
            })
            
        return stats
