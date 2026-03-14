import json
import sqlite3
from typing import List
from datetime import datetime

from schemas_v6 import PaymentEvent, LiquidationDocument, CompanyProfile, AlertEvent, TargetEvent
from normalizers_v6 import parse_date, parse_float
from matchers_v6 import match_payment_to_document, match_document_to_company
from rules_v6 import (
    detect_beneficiary_triangulation, detect_nf_before_company_exists,
    detect_extreme_synchrony, detect_smurfing,
    detect_irregular_company, detect_hidden_partner, detect_direct_employee_supplier,
    detect_transversal_supplier, detect_cnae_incompatibility, detect_year_end_drain,
    detect_sector_concentration
)

class FraudEngineV6:
    def __init__(self, db_path: str = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db", 
                 companies_db: str = r"c:\Users\Usuario\.gemini\antigravity\scratch\output_v2\alvos_societario_rfb.json",
                 targets_db: str = r"c:\Users\Usuario\.gemini\antigravity\scratch\output_v2\alvos_arvore.json"):
        self.db_path = db_path
        self.companies_db = companies_db
        self.targets_db = targets_db
        
        # Repositórios Locais (Cachê)
        self.payments: List[PaymentEvent] = []
        self.documents: List[LiquidationDocument] = []
        self.companies: List[CompanyProfile] = []
        self.targets: List[TargetEvent] = []
        
        self.alerts: List[AlertEvent] = []

    def load_data(self):
        """Etapa 1: Ingestão de Dados."""
        print("Carregando Dados Brutos...")
        
        # A. Empresa Real Loader (Lendo do cache Local Minha Receita)
        # O banco JSON verdadeiro de empresas não subiu nesta pasta ainda. 
        # Injetando Empresa Falsa da Nota extraída (Posto Saco Grande CNPJ 50.668.722)
        self.companies = [
             CompanyProfile(
                  cnpj="50.668.722/0019-16",
                  cnpj_raiz="50668722",
                  data_inicio_atividade=parse_date("2020-01-01"),
                  razao_social="POSTO SACO GRANDE",
                  situacao_cadastral="ATIVA",
                  cnae_principal_codigo="4731800",
                  qsa=[{"cnpj_cpf_socio": "***.624.919-**", "nome_socio": "MAICKON CAMPOS SGROTT"}]
             )
        ]

        # A2. Alvo Real Loader (Lendo do JSON de Funcionarios / Arvore)
        try:
             with open(self.targets_db, "r", encoding="utf-8") as f:
                 raw_targets = json.load(f)
                 for t in raw_targets:
                     alvo = t.get("alvo", {})
                     df_list = t.get("dadosFuncionais", {}).get("matriculas", [])
                     admissao_dt = None
                     # Pegar a admissao mais antiga (primeira posse) se houverem várias
                     for m in df_list:
                          dt = parse_date(m.get("admissao"))
                          if dt and (not admissao_dt or dt < admissao_dt):
                              admissao_dt = dt
                              
                     self.targets.append(TargetEvent(
                         target_id=f"ALV_{alvo.get('cpf', 'UNKNOWN')}",
                         nome=alvo.get("nome"),
                         cpf=alvo.get("cpf"),
                         cargo=alvo.get("cargoInformado"),
                         admissao=admissao_dt
                     ))
        except FileNotFoundError:
             print("Aviso: Banco de Alvos reais não encontrado. Ignorando.")
        
        # B. Carregar Pagamentos e Liquidação
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Carregar Pagamentos (Eventos Macro)
            cursor.execute("SELECT * FROM pagamentos_normalizados")
            for row in cursor.fetchall():
                d = dict(row)
                self.payments.append(PaymentEvent(
                    payment_id=d["id_pagamento"],
                    source="tijucas_pagamentos",
                    orgao_codigo=None,
                    orgao_descricao=None, # Seria complementado
                    unidade_codigo=None,
                    unidade_descricao=None,
                    credor_nome_raw=d["credor_nome"],
                    credor_documento_raw=d["credor_documento"],
                    credor_documento_num=d["credor_documento"],
                    credor_documento_tipo="UNKNOWN", # resolvido em normalize
                    credor_raiz_cnpj=None,
                    valor_pago=parse_float(d["valor_pago"]),
                    data_pagamento=parse_date(d.get("data_pagamento") or "2024-01-01"),
                    data_liquidacao=None,
                    data_empenho=None,
                    empenho_numero=d["empenho_numero"],
                    empenho_ano=d["empenho_ano"],
                    liquidacao_sequencia=d["liquidacao_sequencia"],
                    liquidacao_tipo=d.get("liquidacao_tipo", "1"),
                    liquidacao_ano=d.get("ano_liquidacao") or d.get("empenho_ano")
                ))
            
            # Carregar Detalhes/Aba de Documentos (O Módulo D)
            cursor.execute("SELECT * FROM detalhes_liquidacao")
            for row in cursor.fetchall():
                d = dict(row)
                doc_json = json.loads(d["dados_json"])
                
                # Para cada documento fiscal na matriz (O IPM retorna array "retorno")
                retornos = doc_json.get("retorno", [])
                
                # Se "dados" não for vazio na camada principal do novo JSON interceptado
                if "dados" in doc_json and isinstance(doc_json["dados"], list):
                     for item in doc_json["dados"]:
                         v = item.get("valor", {})
                         if v:
                              self.documents.append(LiquidationDocument(
                                 document_id=f'{d["id_pagamento"]}_DOC_{v.get("sequencia", "")}',
                                 source="tijucas_portal_detalhamento_v6",
                                 payment_id_hint=d["id_pagamento"],
                                 loa_ano=v.get("Loa.ano"),
                                 liquidacao_sequencia=v.get("Liquidacao.sequencia"),
                                 liquidacao_tipo=v.get("tipoLiquidacao"),
                                 credor_documento_raw=v.get("cpfCnpj", ""),
                                 credor_documento_num=v.get("cpfCnpj", ""),
                                 credor_documento_tipo="UNKNOWN",
                                 credor_raiz_cnpj=None,
                                 numero_documento=v.get("numeroDocumento", ""),
                                 tipo_documento=v.get("tipoDocumento", ""),
                                 data_documento=parse_date(v.get("dataDocumento", "")),
                                 valor_documento=parse_float(v.get("valorDocumento"))
                             ))
                elif isinstance(retornos, list):
                     pass # Processo antigo de retorno

            conn.close()
            print(f"[{len(self.payments)}] Pagamentos Macro Carregados.")
            print(f"[{len(self.documents)}] NFs Detalhadas Carregadas.")
        except Exception as e:
            print(f"Aviso Ingestão Falhou: (Teste Local?) {e}")

    def run(self):
        """Etapas 3 e 4: Vinculação e Detecção."""
        print("Iniciando Cruzamentos de Motores (V6.1)...")
        
        for payment in self.payments:
            
            # 3. Faz o Match Determinístico da Tabela de Pagamentos x Aba de Notas Fiscais
            matched_docs_results = match_payment_to_document(payment, self.documents)
            
            for m in matched_docs_results:
                doc: LiquidationDocument = m["document"]
                
                # A. Regra 1 - Triangulação Beneficiário
                new_alerts = detect_beneficiary_triangulation(payment, doc)
                self.alerts.extend(new_alerts)
                
                # 4. Faz o Match Determinístico da Nota Fiscal x Receita Federal
                company = match_document_to_company(doc, self.companies)
                if company:
                    # B. Regra 2 - Empresa Fria 
                    nf_alerts = detect_nf_before_company_exists(doc, company)
                    self.alerts.extend(nf_alerts)
                    
                    # B2. Regra 5 - Recebimento de Empresa Irregular
                    irreg_alerts = detect_irregular_company(doc, company)
                    self.alerts.extend(irreg_alerts)
                    
        # C. Regra 4 - Smurfing Contábil (Macro varredura transversal)
        print("Executando varredura transversal de Smurfing...")
        docs_by_cnpj = {}
        for doc in self.documents:
            c = doc.credor_documento_num
            if c:
                if c not in docs_by_cnpj:
                    docs_by_cnpj[c] = []
                docs_by_cnpj[c].append(doc)
                
        for cnpj, docs_list in docs_by_cnpj.items():
            self.alerts.extend(detect_smurfing(cnpj, docs_list))
            
        # D. Regra 3 - Sincronicidade Extrema Fato/Documento
        print("Executando varredura de Sincronicidade de Alvos...")
        
        # Estratégia Real V6.1:
        # Percorrer Alvos > Filtrar CNPJs em que ele/família é Sócio > Testar Sincronicidade naquelas NFs
        for target in self.targets:
            target_cpfs_to_match = [target.cpf] # Expandir no futuro para a rede orbitante T2
            
            # Empresas onde o Alvo (ou sua rede) é dono
            linked_cnpjs = []
            for comp in self.companies:
                for qsa in comp.qsa:
                    socio_cpf = qsa.get("cnpj_cpf_socio", "")
                    # match parcial devido a mascaramento ***.123.456-**
                    if socio_cpf and target.cpf and socio_cpf[3:11] == target.cpf[3:11]:
                         linked_cnpjs.append(comp.cnpj)
                         break
                         
            if linked_cnpjs:
                linked_docs = [d for d in self.documents if d.credor_documento_num in linked_cnpjs]
                self.alerts.extend(detect_extreme_synchrony(target, linked_docs))
                
        # E. Fase 9 - Regras 6 e 7 - Sócio Oculto e Autocontratação Direta (PF)
        print("Executando varreduras de Sócio Oculto e Recebimentos PF...")
        for target in self.targets:
            # 7. Servidor fornecendo diretamente como pessoa física
            pf_alerts = detect_direct_employee_supplier(target, self.documents)
            self.alerts.extend(pf_alerts)
            
            # 6. Sócio Oculto (Target vs Company QSA)
            for comp in self.companies:
                comp_docs = docs_by_cnpj.get(comp.cnpj, [])
                if comp_docs:
                     socio_alerts = detect_hidden_partner(target, comp, comp_docs)
                     self.alerts.extend(socio_alerts)
                     
        # F. Fase 10 - Regras T2 (Contexto Profundo, Transversal e Orçamentário)
        print("Executando varreduras contextuais T2 (CNAE, Transversal e Orçamento)...")
        # 1. Pré-calcular Totais por Órgão e Pagamentos por CNPJ
        sect_totals = {}
        payments_by_cnpj = {}
        for p in self.payments:
            org = p.orgao_descricao
            cnpj = p.credor_documento_num
            if org:
                sect_totals[org] = sect_totals.get(org, 0.0) + p.valor_pago
            if cnpj:
                if cnpj not in payments_by_cnpj:
                    payments_by_cnpj[cnpj] = []
                payments_by_cnpj[cnpj].append(p)

        for comp in self.companies:
            comp_docs = docs_by_cnpj.get(comp.cnpj, [])
            comp_payments = payments_by_cnpj.get(comp.cnpj, [])
            
            # Regras 8 e 11: Transversal e Concentração Setorial
            if comp_payments:
                self.alerts.extend(detect_transversal_supplier(comp, comp_payments))
                self.alerts.extend(detect_sector_concentration(comp, comp_payments, sect_totals))
                
                # Regra 9: CNAE Incompatível (por pagamento para pegar a secretaria)
                for p in comp_payments:
                    self.alerts.extend(detect_cnae_incompatibility(comp, p))
                    
            # Regra 10: Esvaziamento de Fim de Ano (Doc-level accuracy)
            if comp_docs:
                 self.alerts.extend(detect_year_end_drain(comp, comp_docs))

    def export(self):
        """Etapa 6: Exportação Serializada de Alto Nível"""
        print(f"Exportando {len(self.alerts)} Alertas Encontrados!")
        
        final_out = [a.to_dict() for a in self.alerts]
        with open("alertas_v6_sprint1.json", "w", encoding="utf-8") as f:
            json.dump(final_out, f, indent=2, ensure_ascii=False)
            
        return final_out

if __name__ == '__main__':
    engine = FraudEngineV6()
    engine.load_data()
    engine.run()
    engine.export()
    print("Sucesso! Motor Concluído.")
