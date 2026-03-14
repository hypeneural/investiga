from collections import defaultdict
from .utils import relevant_surnames, COMMON_SURNAMES, FIRST_NAME_TOKENS, _EXCLUDED_SURNAME_TOKENS, all_surnames, normalize_name, parse_value, is_cpf, extract_human_name_from_credor
from .loaders import SECTOR_OWNERSHIP

# Need is_internal_creditor logic to avoid summing government entities as "family"
from .sector_analysis import is_internal_creditor


# ──────────────────────────────────────────────────────────
# V4.1.1: LINK STRENGTH CLASSIFICATION
# ──────────────────────────────────────────────────────────

class LinkStrength:
    FORTE = "FORTE"
    MEDIO = "MEDIO"
    FRACO = "FRACO"


def classify_credor_link_fast(family_surnames_set: set, cred_surnames: list, surname_freq: dict) -> dict:
    """
    V4.1.1a: Fast version — takes PRE-COMPUTED creditor surnames.
    No normalize_name/extract_human_name calls here.
    
    Returns: {"forca": FORTE|MEDIO|FRACO|None, "motivo": str, "matches": list}
    """
    matching = [s for s in family_surnames_set if s in cred_surnames]
    
    if not matching:
        return {"forca": None, "motivo": "sem_match", "matches": []}
    
    # Count how many of the matching surnames are RARE
    rare_matches = []
    common_matches = []
    for s in matching:
        freq = surname_freq.get(s, 0)
        if freq < 5:
            rare_matches.append(s)
        else:
            common_matches.append(s)
    
    if len(rare_matches) >= 2:
        return {
            "forca": LinkStrength.FORTE,
            "motivo": f"2+ sobrenomes raros em comum: {', '.join(rare_matches)}",
            "matches": matching
        }
    elif len(rare_matches) == 1:
        return {
            "forca": LinkStrength.MEDIO,
            "motivo": f"1 sobrenome raro em comum: {rare_matches[0]}",
            "matches": matching
        }
    else:
        return {
            "forca": LinkStrength.FRACO,
            "motivo": f"apenas sobrenomes comuns: {', '.join(common_matches)}",
            "matches": matching
        }


# ──────────────────────────────────────────────────────────
# V4.1.1: SANITY CHECK CONSTANTS
# ──────────────────────────────────────────────────────────

TETO_SALARIO_MENSAL_NUCLEO = 300_000.0  # R$ 300k/month max per family nucleus
TETO_DESPESA_NUCLEO = 200_000_000.0     # R$ 200M absolute max per nucleus


class FamilyNetworkAnalyzer:
    def __init__(self, funcionarios: list, despesas: list, restos: list):
        self.funcs = funcionarios
        # V4.1.1: Keep despesas and restos SEPARATE (previously concatenated)
        self.despesas_exec = list(despesas)
        self.restos = list(restos)
        self.surname_freq = self._calculate_surname_frequencies()
        
        # V4.1.1a: PRE-AGGREGATE creditor totals by CNPJ/CPF to avoid
        # record-level dedup bug (Bug #2 from code review)
        self.credor_totals_exec = self._aggregate_credor_totals(self.despesas_exec)
        self.credor_totals_restos = self._aggregate_credor_totals(self.restos)

    def _aggregate_credor_totals(self, payments: list) -> dict:
        """
        V4.1.1a: Pre-aggregates total paid per creditor (CNPJ/CPF).
        Also pre-computes surnames for each creditor to avoid repeated
        normalize_name() calls during nucleo assignment.
        Returns: {cpf_cnpj: {"total": float, "nome": str, "orgaos": set, "surnames": set}}
        """
        agg = {}
        for p in payments:
            cpf_cnpj = p.get("cpfCnpjCredor", "")
            nome = p.get("nomeCredor", "")
            if not cpf_cnpj or is_internal_creditor(nome):
                continue
            
            valor = parse_value(p.get("valorPago", ""))
            if valor <= 0:
                continue
                
            data_date = p.get("dataEmpenho", "") or p.get("dataLiquidacao", "") or p.get("dataPagamento", "")
            
            if cpf_cnpj not in agg:
                # Pre-compute surnames ONCE per creditor
                nome_base = extract_human_name_from_credor(nome)
                cred_surnames = set(all_surnames(nome_base))
                agg[cpf_cnpj] = {"total": 0.0, "nome": nome, "orgaos": set(), "surnames": cred_surnames, "primeiro_pagamento": data_date}
            else:
                current_dt = agg[cpf_cnpj].get("primeiro_pagamento", "")
                if data_date:
                    parts_n = data_date.split("/")
                    parts_c = current_dt.split("/")
                    if len(parts_n) == 3 and len(parts_c) == 3:
                        str_n = f"{parts_n[2]}{parts_n[1]}{parts_n[0]}"
                        str_c = f"{parts_c[2]}{parts_c[1]}{parts_c[0]}"
                        if str_n < str_c:
                            agg[cpf_cnpj]["primeiro_pagamento"] = data_date
                    elif not current_dt:
                        agg[cpf_cnpj]["primeiro_pagamento"] = data_date
            
            agg[cpf_cnpj]["total"] += valor
            orgao = p.get("orgaoDescricao", "")
            if orgao:
                agg[cpf_cnpj]["orgaos"].add(orgao)
        
        return agg

    def _calculate_surname_frequencies(self) -> dict:
        """Calculates frequency of all valid surnames across the employee dataset."""
        freq = defaultdict(int)
        for f in self.funcs:
            for s in all_surnames(f.get("nome", "")):
                freq[s] += 1
        return dict(freq)

    def classify_surname(self, surname: str) -> str:
        """Classifies a surname as RARO, COMUM, or MUITO_COMUM based on frequency."""
        if surname in COMMON_SURNAMES or surname in FIRST_NAME_TOKENS:
            return "MUITO_COMUM"
        
        count = self.surname_freq.get(surname, 0)
        if count < 5:
            return "RARO"
        elif count <= 30:
            return "COMUM"
        else:
            return "MUITO_COMUM"

    def analyze_network(self, target_name: str, target_sector: str) -> dict:
        """
        Builds the family network for a target based on surname matching.
        Groups matched employees into "Núcleos Familiares Prováveis".
        
        V4.1.1 changes:
          - Filters out FIRST_NAME_TOKENS and expanded COMMON_SURNAMES
          - Classifies creditor links by strength (FORTE/MEDIO/FRACO)
          - Global dedup of creditors per target (no CNPJ counted twice)
          - Separates despesas from restos
          - Adds sanity checks with warnings
        V4.1.1a fixes:
          - Uses parse_value() instead of parse_salary() for valorPago
          - Aggregates by CNPJ first, then assigns to nuclei (Bug #2)
          - Fixed admissao field name (Bug #5)
        """
        surnames = relevant_surnames(target_name)
        network = {
            "sobrenomesRelevantes": [],
            "nucleosEncontrados": [],
            "sanity_warnings": []  # V4.1.1
        }
        
        # Deduplication map: func_idx -> employee summary
        matched_employees = {}
        
        # Determine controlled organs/units to check "mesmoSetor" more broadly
        ownership = SECTOR_OWNERSHIP.get(target_name, {"orgaos": [], "unidades": []})
        target_orgaos = set(o.lower() for o in ownership["orgaos"])
        target_unidades = set(u.lower() for u in ownership["unidades"])
        
        for s in surnames:
            rarity = self.classify_surname(s)
            
            # Skip MUITO_COMUM surnames as they generate too much noise
            if rarity == "MUITO_COMUM":
                continue
                
            network["sobrenomesRelevantes"].append({"sobrenome": s, "raridade": rarity})
            
            # Find matching employees
            for i, f in enumerate(self.funcs):
                func_name = normalize_name(f.get("nome", ""))
                # Skip the target themselves
                if func_name == normalize_name(target_name):
                    continue
                    
                func_surnames = all_surnames(func_name)
                if s in func_surnames:
                    func_centro_custo = f.get("centroCusto", "").lower()
                    
                    is_same_sector = (target_sector and target_sector.lower() == func_centro_custo) or \
                                     any(to in func_centro_custo for to in target_orgaos) or \
                                     any(tu in func_centro_custo for tu in target_unidades)
                    
                    if i not in matched_employees:
                        matched_employees[i] = {
                            "func_idx": i,
                            "nome": f.get("nome"),
                            "cargo": f.get("cargo"),
                            "centroCusto": f.get("centroCusto"),
                            # V4.1.1a: Fixed field name (Bug #5)
                            "dataAdmissao": f.get("admissao", ""),
                            "sobrenomesMatch": [s],
                            "raridadeMax": rarity,
                            "mesmoSetor": is_same_sector
                        }
                    else:
                        if s not in matched_employees[i]["sobrenomesMatch"]:
                            matched_employees[i]["sobrenomesMatch"].append(s)
                            if rarity == "RARO":
                                matched_employees[i]["raridadeMax"] = "RARO"
                                
        # Group into "Núcleos Familiares" by the surnames match
        nucleos = defaultdict(list)
        for emp in matched_employees.values():
            core_key = " + ".join(sorted(emp["sobrenomesMatch"]))
            nucleos[core_key].append(emp)
            
        # V4.1.1a: GLOBAL dedup of creditors across ALL nuclei for this target
        # Now operates at the CREDITOR level (aggregated), not the record level
        global_credor_seen = set()
        credores_ambiguos = set()
        
        for key, members in nucleos.items():
            # Determine score/strength of this core
            forca = "FRACA"
            
            has_raro = any(m["raridadeMax"] == "RARO" for m in members)
            has_same_sector = any(m["mesmoSetor"] for m in members)
            
            if has_raro and has_same_sector:
                forca = "FORTE"
            elif len(members) >= 3 and has_raro:
                forca = "FORTE"
            elif has_raro:
                forca = "MEDIA"
            elif has_same_sector:
                forca = "MEDIA"
                
            network["nucleosEncontrados"].append({
                "sobrenomesCore": key,
                "forcaEvidencia": forca,
                "qtdMembros": len(members),
                "membros": members
            })
            
        # Sort nucleos by strength and then by size
        def sort_key(n):
            forca_val = {"FORTE": 3, "MEDIA": 2, "FRACA": 1}[n["forcaEvidencia"]]
            return (forca_val, n["qtdMembros"])
            
        network["nucleosEncontrados"].sort(key=sort_key, reverse=True)
        
        # ──────────────────────────────────────────────────────────
        # TRILHA 4: Sanguessuga Municipal (V4.1.1a REDESIGNED)
        # Bug #2 fix: aggregate by CNPJ first, then assign to nuclei
        # ──────────────────────────────────────────────────────────
        for nucleo in network["nucleosEncontrados"]:
            surnames_list = [s.strip() for s in nucleo["sobrenomesCore"].split("+")]
            forca = nucleo["forcaEvidencia"]
            
            # 1. Total de salários da família (Deduplicado por index exato)
            total_salario_mes = 0.0
            seen_funcs = set()
            
            for membro in nucleo["membros"]:
                func_idx = membro["func_idx"]
                if func_idx not in seen_funcs and func_idx < len(self.funcs):
                    seen_funcs.add(func_idx)
                    f = self.funcs[func_idx]
                    # V4.1.1a: salarioBase uses BR format, parse_salary is correct here
                    # but parse_value also handles it if it's a number
                    sal_str = f.get("salarioBase", "")
                    try:
                        # salarioBase comes in BR format "6.891,78"
                        sal = float(sal_str.replace(".", "").replace(",", ".")) if sal_str else 0.0
                    except (ValueError, AttributeError):
                        sal = 0.0
                    total_salario_mes += sal
                    
            # SANITY CHECK: Cap salary
            if total_salario_mes > TETO_SALARIO_MENSAL_NUCLEO:
                network["sanity_warnings"].append({
                    "tipo": "SANITY_SALARIO_ALTO",
                    "nucleo": nucleo["sobrenomesCore"],
                    "valor_original": round(total_salario_mes, 2),
                    "valor_capado": TETO_SALARIO_MENSAL_NUCLEO,
                    "motivo": f"Salário mensal do núcleo ({total_salario_mes:,.2f}) excede teto plausível ({TETO_SALARIO_MENSAL_NUCLEO:,.2f})"
                })
                total_salario_mes = TETO_SALARIO_MENSAL_NUCLEO
                
            nucleo["totalSalariosMesFam"] = round(total_salario_mes, 2)
            
            # ──────────────────────────────────────────────────────
            # 2. V4.1.1a: CREDITOR-LEVEL aggregation (Bug #2 fix)
            # Instead of iterating every payment record, iterate
            # pre-aggregated creditor totals and classify once per CNPJ
            # ──────────────────────────────────────────────────────
            total_despesas_exec = 0.0
            total_despesas_restos = 0.0
            credores_fortes = set()
            credores_medios = set()
            credores_fracos = set()
            orgaos_faturados = set()
            
            # V4.1.1: Only compute for FORTE and MEDIA nuclei
            surnames_set = set(surnames_list)
            
            if forca in ["FORTE", "MEDIA"]:
                # Process exercício despesas — iterate CREDITORS, not records
                for cpf_cnpj, cred_data in self.credor_totals_exec.items():
                    # V4.1.1a: Use pre-computed surnames for fast lookup
                    link = classify_credor_link_fast(surnames_set, cred_data["surnames"], self.surname_freq)
                    
                    if link["forca"] is None:
                        continue
                        
                    # Skip if already assigned to another nucleus of this target
                    if cpf_cnpj in global_credor_seen:
                        # V4.2 Hotfix 3: Register ambiguity if it matches multiple nuclei
                        credores_ambiguos.add(cpf_cnpj)
                        continue
                    
                    if link["forca"] == LinkStrength.FORTE:
                        total_despesas_exec += cred_data["total"]
                        credores_fortes.add(cpf_cnpj)
                        orgaos_faturados.update(cred_data["orgaos"])
                        global_credor_seen.add(cpf_cnpj)
                    elif link["forca"] == LinkStrength.MEDIO:
                        total_despesas_exec += cred_data["total"]
                        credores_medios.add(cpf_cnpj)
                        orgaos_faturados.update(cred_data["orgaos"])
                        global_credor_seen.add(cpf_cnpj)
                    else:
                        credores_fracos.add(cpf_cnpj)
                        # FRACO: register but DO NOT sum
                
                # Process restos a pagar — same approach
                for cpf_cnpj, cred_data in self.credor_totals_restos.items():
                    link = classify_credor_link_fast(surnames_set, cred_data["surnames"], self.surname_freq)
                    
                    if link["forca"] is None:
                        continue
                        
                    if cpf_cnpj in global_credor_seen:
                        credores_ambiguos.add(cpf_cnpj)
                        continue
                    
                    if link["forca"] in [LinkStrength.FORTE, LinkStrength.MEDIO]:
                        total_despesas_restos += cred_data["total"]
                        if link["forca"] == LinkStrength.FORTE:
                            credores_fortes.add(cpf_cnpj)
                        else:
                            credores_medios.add(cpf_cnpj)
                        orgaos_faturados.update(cred_data["orgaos"])
                        global_credor_seen.add(cpf_cnpj)
                    else:
                        credores_fracos.add(cpf_cnpj)
            
            total_despesas_fam = total_despesas_exec + total_despesas_restos
            
            # SANITY CHECK: Cap despesas
            if total_despesas_fam > TETO_DESPESA_NUCLEO:
                network["sanity_warnings"].append({
                    "tipo": "SANITY_DESPESA_IMPLAUSIVEL",
                    "nucleo": nucleo["sobrenomesCore"],
                    "valor_original": round(total_despesas_fam, 2),
                    "valor_capado": TETO_DESPESA_NUCLEO,
                    "motivo": f"Total despesas do núcleo ({total_despesas_fam:,.2f}) excede teto plausível ({TETO_DESPESA_NUCLEO:,.2f})"
                })
                # Proportionally cap
                if total_despesas_fam > 0:
                    ratio = TETO_DESPESA_NUCLEO / total_despesas_fam
                    total_despesas_exec *= ratio
                    total_despesas_restos *= ratio
                    total_despesas_fam = TETO_DESPESA_NUCLEO
            
            # V4.1.1: Separated fields
            nucleo["totalDespesasFamExerc"] = round(total_despesas_exec, 2)
            nucleo["totalDespesasFamRestos"] = round(total_despesas_restos, 2)
            nucleo["totalDespesasFam"] = round(total_despesas_fam, 2)
            
            nucleo["qtdCredoresFortes"] = len(credores_fortes)
            nucleo["qtdCredoresMedios"] = len(credores_medios)
            nucleo["qtdCredoresFracos"] = len(credores_fracos)
            nucleo["qtdCredoresLigadosFam"] = len(credores_fortes) + len(credores_medios)
            nucleo["qtdOrgaosFaturadosFam"] = len(orgaos_faturados)
            
            # V4.2: Export lists for transversal analysis
            credores_detalhes = {}
            for c in credores_fortes.union(credores_medios):
                c_data = self.credor_totals_exec.get(c, {})
                c_data_restos = self.credor_totals_restos.get(c, {})
                dt1 = c_data.get("primeiro_pagamento", "")
                dt2 = c_data_restos.get("primeiro_pagamento", "")
                
                earliest = dt1
                if dt2:
                    if not dt1:
                        earliest = dt2
                    else:
                        p1 = dt1.split("/")
                        p2 = dt2.split("/")
                        if len(p1)==3 and len(p2)==3:
                            s1 = f"{p1[2]}{p1[1]}{p1[0]}"
                            s2 = f"{p2[2]}{p2[1]}{p2[0]}"
                            if s2 < s1: earliest = dt2
                            
                credores_detalhes[c] = {
                    "nome": c_data.get("nome") or c_data_restos.get("nome", ""),
                    "primeiroPagamento": earliest
                }
                
            nucleo["credoresFortes"] = list(credores_fortes)
            nucleo["credoresMedios"] = list(credores_medios)
            nucleo["credoresDetalhes"] = credores_detalhes
            
            # V4.1.1: Trigger alert only for FORTE nuclei with real financial activity
            if forca == "FORTE" and (total_despesas_fam > 50000 or len(orgaos_faturados) >= 3 or total_salario_mes > 20000):
                nucleo["alertaSanguessuga"] = "CONCENTRACAO_FAMILIAR_MUNICIPAL"
            elif forca == "MEDIA" and (total_despesas_fam > 100000 or len(orgaos_faturados) >= 5):
                # V4.1.1: MEDIA only triggers with higher thresholds
                nucleo["alertaSanguessuga"] = "CONCENTRACAO_FAMILIAR_MUNICIPAL_HIPOTESE"
            else:
                nucleo["alertaSanguessuga"] = False
                
        # V4.2: Hotfix 3
        network["credoresAmbiguosEntreNucleos"] = list(credores_ambiguos)
        return network
