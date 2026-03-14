import sqlite3
import json
import os
import hashlib
from datetime import datetime
from collections import defaultdict

# Caminhos
# O banco que tem todos os metadados NLP, Detalhes e Sancionados reais está aqui:
DB_RAW = 'c:/Users/Usuario/.gemini/antigravity/scratch/scrapers/output_scraping/tijucas_raw.db'
DB_TJC = 'c:/Users/Usuario/.gemini/antigravity/scratch/scrapers/output_scraping/tijucas_raw.db'
OUTPUT_DIR = 'c:/Users/Usuario/.gemini/antigravity/scratch/investiga-tijucas/src/data/generated'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_node_id(prefix, raw_val):
    return f"{prefix}_{hashlib.md5(str(raw_val).encode('utf-8')).hexdigest()[:10]}"

def run_export():
    print("Iniciando Exportador de Dados para Frontend V2...")
    
    conn = sqlite3.connect(DB_RAW)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute(f"ATTACH DATABASE '{DB_TJC}' AS tjc")

    # 1. Carregar Fornecedores
    c.execute('''
        SELECT 
            p.credor_documento, 
            MAX(p.credor_nome) as credor_nome,
            SUM(p.valor_pago) as total_recebido,
            COUNT(p.id_pagamento) as qtd_pagamentos,
            MAX(s.has_sanction) as has_sanction,
            MAX(s.has_pep_match) as has_pep,
            MAX(s.has_ceis_cnep) as has_ceis_cnep,
            MAX(s.has_qsa) as has_qsa,
            MAX(s.raw_graph_json) as raw_graph_json
        FROM pagamentos_normalizados p
        LEFT JOIN tjc.supplier_national_context s 
            ON REPLACE(REPLACE(REPLACE(p.credor_documento, '.', ''), '/', ''), '-', '') = REPLACE(REPLACE(REPLACE(s.cnpj, '.', ''), '/', ''), '-', '')
        GROUP BY p.credor_documento
    ''')
    fornecedores_raw = c.fetchall()
    
    nodes_pj = {}
    hubs = defaultdict(list)
    sancionados = []
    
    for f in fornecedores_raw:
        doc = f['credor_documento']
        if not doc or len(doc) < 11: continue
        
        score = 0
        badges = []
        
        if f['has_sanction'] or f['has_ceis_cnep']:
            score += 40
            badges.append("SANCIONADO")
            sancionados.append(f)
            
        if f['has_pep']:
            score += 15
            badges.append("PEP")
            
        if f['has_qsa']:
            badges.append("TEM_SOCIEDADES")
            
        # Parse graph for contacts
        telefone, email, endereco = "Desconhecido", "Desconhecido", "Desconhecido"
        cnae = "Desconhecido"
        socios = []
        
        if f['raw_graph_json']:
            try:
                graph = json.loads(f['raw_graph_json'])
                # If BrasilAPI format
                if "cnae_fiscal_descricao" in graph:
                    cnae = graph.get("cnae_fiscal_descricao", cnae)
                    
                    email_str = graph.get("email")
                    if email_str: email = email_str
                    
                    telefone_str = graph.get("ddd_telefone_1")
                    if telefone_str: telefone = telefone_str
                    
                    logradouro = graph.get("logradouro", "")
                    numero = graph.get("numero", "")
                    bairro = graph.get("bairro", "")
                    municipio = graph.get("municipio", "")
                    uf = graph.get("uf", "")
                    if logradouro and municipio:
                        endereco = f"{logradouro}, {numero} - {bairro}, {municipio}/{uf}".strip(" -,")
                        
                    for socio in graph.get("qsa", []):
                        nome_socio = socio.get("nome_socio")
                        if nome_socio and nome_socio != (f['credor_nome'] or "Desconhecido") and nome_socio not in socios:
                            socios.append(nome_socio)
                # If Old BRACC format
                else:
                    for n in graph.get('nodes', []):
                        labels = n.get('labels', [])
                        props = n.get('properties', {})
                        if "Company" in labels and props.get('id') == doc:
                            cnae = props.get('taxId', cnae) 
                        if "Contact" in labels:
                            if props.get('type') == 'phone': telefone = props.get('value', telefone)
                            if props.get('type') == 'email': email = props.get('value', email)
                        if "Address" in labels:
                            endereco = props.get('fullAddress', endereco)
                        if "Person" in labels or "Partner" in labels or "Socio" in labels or "Company" in labels:
                            nome_socio = props.get('name') or props.get('nome') or props.get('razao_social') or props.get('nome_socio')
                            if nome_socio and nome_socio != (f['credor_nome'] or "Desconhecido") and nome_socio not in socios:
                                socios.append(nome_socio)
            except Exception as e:
                pass
            
        score = min(100, score)
        risk_level = "low"
        if score >= 75: risk_level = "critical"
        elif score >= 50: risk_level = "high"
        elif score >= 25: risk_level = "medium"
        
        node_id = get_node_id('pj', doc)
        
        nodes_pj[doc] = {
            "id": node_id,
            "label": f['credor_nome'] or "Desconhecido",
            "type": "credor_pf" if len(doc) == 11 else "credor_pj",
            "risk_level": risk_level,
            "score": score,
            "badges": list(set(badges)),
            "totals": {
                "valor_recebido": f['total_recebido'] or 0,
                "qtd_pagamentos": f['qtd_pagamentos'],
                "qtd_alertas": 1 if f['has_sanction'] else 0
            },
            "metadata": {
                "documento": doc,
                "status_receita": "Ativa", # hardcode por enquanto
                "fundacao": "N/A",
                "cnae_primario": cnae,
                "telefone": telefone,
                "email": email,
                "endereco": endereco,
                "socios": socios,
                "sancoes": [{"fonte": "BR-ACC (CEIS)"}] if f['has_sanction'] else []
            }
        }
        
        if telefone != "Desconhecido": hubs[telefone].append(doc)
        if email != "Desconhecido": hubs[email].append(doc)
        if endereco != "Desconhecido": hubs[endereco].append(doc)

    # 3. Órgãos e Pagamentos (Edges Base)
    # Aqui também faremos lógica simples para Fracionamento Frio
    c.execute('''
        SELECT 
            COALESCE(json_extract(p.raw_data, '$.entidade'), 'Prefeitura Municipal de Tijucas') as orgao_nome,
            p.credor_documento,
            strftime('%Y-%m', p.data_pagamento) as mes_ano,
            SUM(p.valor_pago) as valor_total,
            COUNT(*) as qtd_pagamentos,
            MIN(p.data_pagamento) as min_data,
            MAX(p.data_pagamento) as max_data
        FROM pagamentos_normalizados p
        WHERE p.credor_documento IS NOT NULL
        GROUP BY orgao_nome, p.credor_documento, mes_ano
    ''')
    pagamentos_agrupados_mes = c.fetchall()
    
    # Agrupar orgão x doc geral
    pagamentos_agrupados = defaultdict(lambda: {"valor_total": 0, "qtd_pagamentos": 0, "min_data": "2099", "max_data": "1900"})
    fracionamentos = []
    
    for pag in pagamentos_agrupados_mes:
        orgao = pag['orgao_nome'] or "Órgao Desconhecido"
        doc = pag['credor_documento']
        if doc not in nodes_pj: continue
        
        k = f"{orgao}::{doc}"
        pagamentos_agrupados[k]['valor_total'] += float(pag['valor_total'] or 0)
        pagamentos_agrupados[k]['qtd_pagamentos'] += int(pag['qtd_pagamentos'] or 0)
        pagamentos_agrupados[k]['min_data'] = min(str(pagamentos_agrupados[k]['min_data']), str(pag['min_data'] or '2099'))
        pagamentos_agrupados[k]['max_data'] = max(str(pagamentos_agrupados[k]['max_data']), str(pag['max_data'] or '1900'))
        
        # Detecção de Fracionamento (muitos pagamentos pequenos no mesmo mês somando muito)
        valor_pag = float(pag['valor_total'] or 0)
        qtd = int(pag['qtd_pagamentos'] or 0)
        if qtd >= 3 and 10000 <= valor_pag <= 55000:
             nodes_pj[doc]['score'] = min(100, nodes_pj[doc]['score'] + 20)
             nodes_pj[doc]['badges'].append("FRACIONAMENTO")
             fracionamentos.append({
                 "orgao": orgao,
                 "doc": doc,
                 "mes": pag['mes_ano'],
                 "valor": pag['valor_total'],
                 "qtd": pag['qtd_pagamentos']
             })

    nodes_orgao = {}
    edges_pagamento = []
    
    for k, pag in pagamentos_agrupados.items():
        orgao, doc = k.split("::")
        org_id = get_node_id('org', orgao)
        
        if org_id not in nodes_orgao:
            nodes_orgao[org_id] = {
                "id": org_id,
                "label": orgao,
                "type": "orgao",
                "risk_level": "low",
                "score": 0,
                "metadata": {}
            }
            
        peso_valor = min(10, max(1, int(float(pag['valor_total'] or 0) / 100000)))
        edge_id = f"edge_pag_{org_id}_{nodes_pj[doc]['id']}"
        
        edges_pagamento.append({
            "id": edge_id,
            "source": org_id,
            "target": nodes_pj[doc]['id'],
            "type": "pagamento_direto",
            "risk_level": nodes_pj[doc]['risk_level'],
            "weight": peso_valor,
            "label": f"R$ {pag['valor_total']:,.2f}",
            "badges": nodes_pj[doc]['badges'],
            "metadata": {
                "valor_total": pag['valor_total'],
                "qtd_pagamentos": pag['qtd_pagamentos'],
                "periodo_inicio": pag['min_data'],
                "periodo_fim": pag['max_data']
            }
        })
        
        if nodes_pj[doc]['score'] >= 50:
            nodes_orgao[org_id]['score'] += 5

    for oid, o in nodes_orgao.items():
        o['score'] = min(100, o['score'])
        if o['score'] >= 75: o['risk_level'] = "critical"
        elif o['score'] >= 50: o['risk_level'] = "high"
        elif o['score'] >= 25: o['risk_level'] = "medium"

    # 4. Arestas de Hub Compartilhado
    edges_hubs = []
    hub_count = 0
    fraud_hubs = []
    
    for h_val, docs in hubs.items():
        if len(docs) > 1 and len(docs) <= 10: 
            hub_count += 1
            docs_obj = [nodes_pj[d] for d in docs if d in nodes_pj]
            if len(docs_obj) < 2: continue
            
            for i in range(len(docs_obj)):
                for j in range(i+1, len(docs_obj)):
                    edges_hubs.append({
                        "id": f"edge_hub_{hub_count}_{i}_{j}",
                        "source": docs_obj[i]['id'],
                        "target": docs_obj[j]['id'],
                        "type": "empresa_mesmo_hub",
                        "risk_level": "high",
                        "weight": 5,
                        "label": "Contato Compartilhado",
                        "badges": ["HUB_SUSPEITO"],
                        "metadata": {
                            "hub_type": "telefone/email",
                            "shared_value_masked": h_val[:3] + "***" + h_val[-4:],
                            "confidence": "high"
                        }
                    })
                    docs_obj[i]['score'] = min(100, int(docs_obj[i]['score']) + 15)
                    docs_obj[j]['score'] = min(100, int(docs_obj[j]['score']) + 15)
            
            fraud_hubs.append({
                "id": f"hub_{hub_count}",
                "gravidade": "HIGH",
                "score": max([int(d['score']) for d in docs_obj]),
                "entidade_principal": docs_obj[0]['label'],
                "entidades_relacionadas": [d['label'] for d in docs_obj[1:]],
                "valor_total": sum([float(d['totals']['valor_recebido']) for d in docs_obj]),
                "why_flagged": f"As empresas dividem ativamente o mesmo contato ({h_val[:3] + '***' + h_val[-4:]}). Indício de coordenação."
            })

    # 5. Filtrar Grafo (Investigativo)
    valid_nodes = []
    for doc, n in nodes_pj.items():
        if n['score'] >= 25 or n['totals']['valor_recebido'] > 500000:
            valid_nodes.append(n)
    
    valid_orgs = list(nodes_orgao.values())
    
    val_node_ids = {n['id'] for n in valid_nodes + valid_orgs}
    valid_edges = [e for e in edges_pagamento + edges_hubs if e['source'] in val_node_ids and e['target'] in val_node_ids]

    network_graph = {
        "meta": {
            "total_nodes": len(valid_nodes) + len(valid_orgs),
            "total_edges": len(valid_edges)
        },
        "nodes": valid_nodes + valid_orgs,
        "edges": valid_edges
    }

    # 6. Timeline e Anomalias
    c.execute('''
        SELECT 
            p.data_pagamento,
            p.valor_pago,
            p.id_pagamento
        FROM pagamentos_normalizados p
        WHERE p.data_pagamento IS NOT NULL
    ''')
    timeline_raw = c.fetchall()
    
    heatmap_agg = defaultdict(lambda: {"valor_total": 0, "qtd_pagamentos": 0})
    for t in timeline_raw:
        dt = str(t['data_pagamento']).strip()
        ano, mes = 0, 0
        if '/' in dt:
            parts = dt.split('/')
            if len(parts) == 3:
                ano, mes = int(parts[2][:4]), int(parts[1])
        elif '-' in dt:
            parts = dt.split('-')
            if len(parts) >= 2:
                ano, mes = int(parts[0][:4]), int(parts[1])
        if ano > 1900 and 1 <= mes <= 12:
            heatmap_agg[(ano, mes)]['valor_total'] += float(t['valor_pago'] or 0)
            heatmap_agg[(ano, mes)]['qtd_pagamentos'] += 1

    heatmap_series = []
    for (ano, mes), val in heatmap_agg.items():
        heatmap_series.append({
            "ano": ano,
            "mes": mes,
            "valor": val['valor_total'],
            "eventos": val['qtd_pagamentos']
        })
    heatmap_series.sort(key=lambda x: (x['ano'], x['mes']))

    # Fraud Crossings
    
    # Processar Fracionamentos para exportação
    fracionamento_frio = []
    for f in fracionamentos[:20]: # limitar pros top
        fracionamento_frio.append({
             "id": get_node_id('frac', f['doc'] + f['mes']),
             "gravidade": "HIGH",
             "score": nodes_pj[f['doc']]['score'],
             "entidade_principal": nodes_pj[f['doc']]['label'],
             "valor_total": f['valor'],
             "why_flagged": f"Possível fracionamento: {f['qtd']} pagamentos em {f['mes']} somando R$ {f['valor']:,.2f}.",
             "evidence_sources": f['orgao']
        })

    # Ligação Societária QSA
    qsa_edges = []
    for doc, n in nodes_pj.items():
        if "TEM_SOCIEDADES" in n['badges']:
             # Adiciona edge fake para visualização qsa na rede
             pass
    
    # Sincronicidade: Ocorre quando muitas empresas distintas ganham o exato mesmo valor no mesmo dia
    # TODO: Implementar depois na base real

    fraud_crossings = {
        "sancionados_contratados": [{
             "id": get_node_id('san', s['credor_documento']),
             "gravidade": "CRITICAL",
             "score": 100,
             "entidade_principal": s['credor_nome'],
             "valor_total": s['total_recebido'] or 0,
             "why_flagged": "Empresa sancionada ativamente faturando pela prefeitura.",
             "evidence_sources": "BR-ACC (CEIS/CNEP)"
        } for s in sancionados],
        "incompatibilidade_cnae_objeto": [], # IA
        "incompatibilidade_orgao_objeto": [], # IA
        "fracionamento_frio": fracionamento_frio,
        "triangulacao_fachada": fraud_hubs,
        "conflito_interesse": [],
        "sincronicidade_temporal": [],
        "empresa_fenix": [],
        "mesmo_telefone": [h for h in fraud_hubs if "telefone" in h.get("why_flagged", "")],
        "mesmo_email": [h for h in fraud_hubs if "email" in h.get("why_flagged", "")],
        "ligacao_societaria_qsa": []
    }

    # 7. Dashboard KPIs
    t1_alerts = 0
    
    top_credores = sorted(nodes_pj.values(), key=lambda x: float(x['totals']['valor_recebido'] or 0), reverse=True)[:10]
    top_orgaos = sorted(nodes_orgao.values(), key=lambda x: int(x['score'] or 0), reverse=True)[:10]

    dashboard_kpis = {
        "total_monitorado": sum([float(n['totals']['valor_recebido'] or 0) for n in nodes_pj.values()]),
        "total_pagamentos": sum([int(n['totals']['qtd_pagamentos'] or 0) for n in nodes_pj.values()]),
        "total_credores": len(nodes_pj),
        "total_orgaos": len(nodes_orgao),
        "alertas_t1": t1_alerts,
        "alertas_t2": 0,
        "sancionados_contratados": len(sancionados),
        "casos_incompatibilidade_cnae": 0,
        "genericidade_alta": 0,
        "empresas_hub_compartilhado": len(fraud_hubs),
        "top_10_credores_suspeitos": sorted([n for n in valid_nodes if n['score'] >= 50], key=lambda x: x['score'], reverse=True)[:10],
        "top_10_orgaos_risco": top_orgaos
    }

    # 8. Manifest
    manifest = {
        "schema_version": "v2",
        "generated_at": datetime.now().isoformat(),
        "sources": {"tijucas_raw_db": "ok", "tijucas_db": "ok"},
        "counts": {
            "nodes": network_graph['meta']['total_nodes'],
            "edges": network_graph['meta']['total_edges']
        }
    }

    # Extrair Pagamentos Individuais (Adicionando extração de histórico do JSON)
    c.execute('''
        SELECT 
            p.id_pagamento,
            p.credor_documento,
            p.data_pagamento,
            p.valor_pago,
            COALESCE(json_extract(p.raw_data, '$.entidade'), 'Prefeitura Municipal de Tijucas') as orgao_nome,
            COALESCE(
               sem.justificativa_curta, 
               nlp.resumo_auditavel, 
               json_extract(dl.dados_json, '$.dados[0].valor."Liquidacao.historico"'),
               json_extract(dl.dados_json, '$.dados[0].valor."Liquidacao.Empenho.historico"'),
               json_extract(dl.dados_json, '$.dados[0].valor.historico'),
               json_extract(dl.dados_json, '$.dados[0].valor."Liquidacao.Empenho.historicoEmpenho"'),
               json_extract(dl.dados_json, '$.dados[0].valor."Liquidacao.historicoLiquidacao"'),
               'Sem descritivo ou IA indisponível'
            ) as historico_pagamento,
            sem.categoria_primaria as macro_categoria
        FROM pagamentos_normalizados p
        LEFT JOIN tjc.expense_semantic_labels sem ON p.id_pagamento = sem.source_id
        LEFT JOIN tjc.case_nlp_reviews nlp ON p.id_pagamento = nlp.case_id
        LEFT JOIN tjc.detalhes_liquidacao dl ON p.id_pagamento = dl.id_pagamento
        WHERE p.credor_documento IS NOT NULL
        ORDER BY p.data_pagamento DESC
    ''')
    todos_pagamentos_raw = c.fetchall()
    
    pagamentos_por_alvo = defaultdict(list)
    for p in todos_pagamentos_raw:
        doc = p['credor_documento']
        if doc in nodes_pj:
            pagamentos_por_alvo[nodes_pj[doc]['id']].append({
                "data": p['data_pagamento'],
                "valor": p['valor_pago'] or 0,
                "orgao": p['orgao_nome'],
                "historico": p['historico_pagamento'] or ''
            })

    # Salvar Arquivos
    def save_json(filename, data):
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Salvo: {filename}")

    save_json('manifest.json', manifest)
    save_json('dashboard_kpis.json', dashboard_kpis)
    save_json('network_graph_v2.json', network_graph)
    save_json('fraud_crossings.json', fraud_crossings)
    save_json('targets_index.json', valid_nodes + valid_orgs)
    # Mocking os restantes para o frontend não quebrar
    save_json('orgaos_risk.json', list(nodes_orgao.values()))
    save_json('temporal_anomalies.json', {
        "serie_mensal": heatmap_series,
        "concentracao_dezembro": []
    })
    save_json('semantic_overview.json', {"categorias": []})
    save_json('pagamentos_alvos.json', pagamentos_por_alvo)

    print("=== EXPORTAÇÃO FRONTEND CONCLUÍDA ===")

if __name__ == "__main__":
    run_export()
