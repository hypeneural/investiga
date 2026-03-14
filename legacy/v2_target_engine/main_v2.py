import os
from analysis.loaders import load_data, define_targets
from analysis.identity_resolution import IdentityResolver, MatchClass
from analysis.target_resolution import TargetResolver
from analysis.payment_linking import PaymentLinker
from analysis.family_network import FamilyNetworkAnalyzer
from analysis.sector_analysis import SectorAnalyzer
from analysis.cross_target_graph import CrossTargetGraph
from analysis.scoring import TripleScorer
from analysis.sanity_checks import SanityChecker
from analysis.exporters import Exporter
from analysis.transversal import TransversalAnalyzer
from analysis.temporal import TemporalAnalyzer
from analysis.societary import SocietaryAnalyzer
from analysis.utils import parse_salary, parse_value

def main():
    print("=" * 60)
    print("Análise Profunda de Fraudes v2 - Tijucas (SC)")
    print("Foco: Prefeito, Vereadores e Secretários/Diretores")
    print("=" * 60)

    # 1. Load data
    data_dir = os.path.dirname(os.path.abspath(__file__))
    funcs, despesas, restos = load_data(data_dir)
    raw_targets = define_targets()
    
    # 2. Initialize analyzers
    ident_resolver = IdentityResolver(funcs)
    targ_resolver = TargetResolver(funcs)
    pay_linker = PaymentLinker(ident_resolver, despesas, restos)
    fam_analyzer = FamilyNetworkAnalyzer(funcs, despesas, restos)
    sec_analyzer = SectorAnalyzer(funcs, despesas, restos)
    
    print("\n[Etapa 1] Resolvendo pagamentos e identidades base...")
    pay_linker.resolve_all_payments()
    
    print("[Etapa 2] Construindo árvores por alvo (resolução fuzzy)...")
    target_trees = []
    
    for raw_t in raw_targets:
        matches = targ_resolver.resolve_target(raw_t)
        
        # Build base target node
        alvo_node = {
            "nome": raw_t["nome"],
            "tipo": "politico",
            "cargoInformado": raw_t["cargo"],
            "statusResolucao": "nao_encontrado",
            "confiancaResolucao": 0.0
        }
        
        tree = {
            "alvo": alvo_node,
            "dadosFuncionais": {},
            "pagamentosDiretos": {},
            "redeFamiliar": {},
            "redeSetor": {},
            "redeCredoresDoSetor": {}, # NOVO BLOCO V3
            "conexoesCruzadas": {},
            "scores": {},
            "alertas": []
        }
        
        if matches:
            best_match = matches[0]
            func_data = best_match["func"]
            idx = funcs.index(func_data)
            
            alvo_node["statusResolucao"] = best_match["status"]
            alvo_node["confiancaResolucao"] = best_match["confianca"]
            alvo_node["cpf"] = func_data.get("cpf", "")
            
            # Dados Funcionais - Find all records for this person (Fix for Bug B)
            same_person_records = ident_resolver.find_all_person_records(func_data)
            
            tree["dadosFuncionais"] = {
                "matriculas": same_person_records,
                "cargo": func_data.get("cargo", ""),
                "salarioBase": parse_salary(func_data.get("salarioBase", "")),
                "centroCusto": func_data.get("centroCusto", ""),
                "situacao": func_data.get("situacao", "")
            }
            
            # Pagamentos
            total_pago = 0.0
            fortes = 0
            medias = 0
            ambiguos = 0
            todas_despesas = []
            todos_restos = []
            
            # V4.1.1a: Dedup payments across multiple matrículas (Bug #3)
            # Use payment key to avoid counting the same payment twice
            seen_payment_keys = set()
            
            # Aggregate payments from ALL indices representing this person
            for record in same_person_records:
                record_idx = funcs.index(record)
                payments = pay_linker.get_payments_for_funcionario(record_idx)
                
                for p in payments.get("despesas", []):
                    d = p["despesa"]
                    # V4.2: Refining pay_key to include year/month/date to avoid collapsing distinct monthly payments
                    pay_key = (
                        "desp",
                        d.get("cpfCnpjCredor", ""),
                        d.get("orgaoCodigo", ""),
                        d.get("unidadeCodigo", ""),
                        str(d.get("valorPago", "")),
                        d.get("_ano", ""),
                        d.get("_mes", ""),
                        d.get("dataPagamento", d.get("dataLiquidacao", "")),
                        d.get("nomeCredor", "")[:30],
                    )
                    if pay_key not in seen_payment_keys:
                        seen_payment_keys.add(pay_key)
                        todas_despesas.append(p)
                        total_pago += parse_value(d.get("valorPago", 0))
                        cls = p["evidencia"]["classe"]
                        if cls in (MatchClass.EXATO_FORTE, MatchClass.FORTE):
                            fortes += 1
                        elif cls == MatchClass.MEDIA:
                            medias += 1
                        elif cls in (MatchClass.FRACA, MatchClass.AMBIGUA):
                            ambiguos += 1
                
                for p in payments.get("restos", []):
                    r = p["resto"]
                    pay_key = (
                        "rest",
                        r.get("cpfCnpjCredor", ""),
                        r.get("orgaoCodigo", ""),
                        r.get("unidadeCodigo", ""),
                        str(r.get("valorPago", "")),
                        r.get("_ano", ""),
                        "", # restos don't usually have _mes
                        r.get("dataPagamento", r.get("dataLiquidacao", "")),
                        r.get("nomeCredor", "")[:30],
                    )
                    if pay_key not in seen_payment_keys:
                        seen_payment_keys.add(pay_key)
                        todos_restos.append(p)
                        total_pago += parse_value(r.get("valorPago", 0))
                        cls = p["evidencia"]["classe"]
                        if cls in (MatchClass.EXATO_FORTE, MatchClass.FORTE):
                            fortes += 1
                        elif cls == MatchClass.MEDIA:
                            medias += 1
                        elif cls in (MatchClass.FRACA, MatchClass.AMBIGUA):
                            ambiguos += 1
                
            tree["pagamentosDiretos"] = {
                "totalPago": total_pago,
                "qtdMatchesFortes": fortes,
                "qtdMatchesMedios": medias,
                "qtdMatchesAmbiguos": ambiguos,
                "detalhesDespesas": todas_despesas,
                "detalhesRestos": todos_restos
            }
            
            # Rede Familiar
            tree["redeFamiliar"] = fam_analyzer.analyze_network(func_data.get("nome", ""), func_data.get("centroCusto", ""))
            
            # V4.1.1a: Promote redeFamiliar sanity_warnings to tree level (Bug #4)
            tree["sanity_warnings"] = tree.get("sanity_warnings", []) + tree["redeFamiliar"].get("sanity_warnings", [])
            
            # Rede Setor
            tree["redeSetor"] = sec_analyzer.analyze_sector(func_data.get("centroCusto", ""))
            
            # Rede Credores do Setor (Financeiro)
            # V4.1.1a: Try resolved name first, fallback to raw name for SECTOR_OWNERSHIP lookup (Bug #6)
            resolved_name = func_data.get("nome", "")
            sector_lookup_name = raw_t["nome"]  # SECTOR_OWNERSHIP keys match define_targets() names
            
            # V4.2: Adicionar diagnósticos do lookup setorial (Hotfix 4)
            sect_res = sec_analyzer.analyze_sector(func_data.get("centroCusto", ""))
            
            tree["redeSetor"] = sect_res
            
            tree["redeCredoresDoSetor"] = sec_analyzer.analyze_sector_financials(sector_lookup_name)
            
            tree["diagnosticoSetorial"] = {
                "alvo": resolved_name,
                "chaveLookupUsada": sector_lookup_name,
                "totalCredoresPagos": len(tree["redeCredoresDoSetor"].get("topCredoresCNPJPrivados", [])) + len(tree["redeCredoresDoSetor"].get("topCredoresPFPrivados", []))
            }
            
        target_trees.append(tree)

    print("[Etapa 3] Construindo conexões cruzadas...")
    cross_graph = CrossTargetGraph(target_trees)
    for i, tree in enumerate(target_trees):
        if tree["alvo"]["statusResolucao"] != "nao_encontrado":
            tree["conexoesCruzadas"] = cross_graph.find_connections(i)
            
    print("[Etapa 3.5] V4.2 - Mapeando Fornecedores Transversais (Cartéis)...")
    trans_analyzer = TransversalAnalyzer(target_trees)
    global_transversal_alerts = trans_analyzer.analyze()
    print(f"  Detectados {len(global_transversal_alerts)} credores transversais suspeitos.")
    
    print("[Etapa 3.6] V4.3 - Mapeando Anomalias Temporais (Fim de Ano)...")
    temporal_analyzer = TemporalAnalyzer(despesas, restos)
    global_temporal_alerts = temporal_analyzer.analyze_end_of_year_anomalies()
    print(f"  Detectados {len(global_temporal_alerts)} credores com pico de fim de ano.")
    
    for tree in target_trees:
        if tree["alvo"]["statusResolucao"] == "nao_encontrado":
            continue
            
        target_temporal_alerts = []
        # Check family creditors
        rf = tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        for nucleo in rf:
            for c_cnpj in nucleo.get("credoresFortes", []) + nucleo.get("credoresMedios", []):
                if c_cnpj in global_temporal_alerts:
                    alert = global_temporal_alerts[c_cnpj].copy()
                    alert["origem"] = f"Familiar ({nucleo['sobrenomesCore']})"
                    alert["cnpj"] = c_cnpj
                    target_temporal_alerts.append(alert)
                    
        # Check sector top creditors
        top_cred = tree.get("redeCredoresDoSetor", {}).get("topCredoresCNPJPrivados", [])
        for c in top_cred:
            c_cnpj = c.get("documento")
            if c_cnpj in global_temporal_alerts:
                # Add only if not already there
                if not any(a["cnpj"] == c_cnpj for a in target_temporal_alerts):
                    alert = global_temporal_alerts[c_cnpj].copy()
                    alert["origem"] = "Setor Dominado"
                    alert["cnpj"] = c_cnpj
                    target_temporal_alerts.append(alert)
                    
        tree["temporal_alerts"] = target_temporal_alerts
            
    print("[Etapa 3.7] V5.0 - Enriquecendo dados societários (Minha Receita)...")
    for tree in target_trees:
        if tree["alvo"]["statusResolucao"] != "nao_encontrado":
            soc_auth = SocietaryAnalyzer(tree)
            soc_auth.analyze()
            
    print("[Etapa 4] Calculando Triplo Score V3 (Financeiro, Relacional, Evidência)...")
    for tree in target_trees:
        if tree["alvo"]["statusResolucao"] != "nao_encontrado":
            scorer = TripleScorer(tree)
            scores = scorer.calculate_scores()
            tree["scores"] = {
                "riscoFinanceiro": scores["risco_financeiro"], 
                "riscoRelacional": scores["risco_relacional"], 
                "evidencia": scores["evidencia"]
            }
            tree["alertas"] = scores["alertas"]

    print("[Etapa 4.5] V4.1.1 — Validando sanidade dos dados...")
    checker = SanityChecker()
    global_warnings = checker.validate_all(target_trees)
    print(f"  Sanity warnings globais: {len(global_warnings)}")
    for w in global_warnings[:10]:
        print(f"  ⚠️  [{w['tipo']}] {w.get('motivo', '')}")

    print("[Etapa 5] Exportando resultados JSON e Markdown...")
    exporter = Exporter(os.path.join(data_dir, "output_v2"))
    
    exporter.export_json("alvos_arvore.json", target_trees)
    
    # Audit matches
    audit = {"despesas": pay_linker.linked_despesas, "restos": pay_linker.linked_restos}
    exporter.export_json("auditoria_matches.json", audit)
    
    # Markdown Report
    exporter.export_markdown("relatorio_fraudes_v2.md", target_trees)
    
    print("\n" + "="*60)
    print("Concluído! Relatórios gerados em 'output_v2/'")

if __name__ == "__main__":
    main()
