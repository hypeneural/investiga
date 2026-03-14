import sqlite3
import json

DB_PATH = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db"

class HybridFraudEngineV8:
    def __init__(self, db_path):
        self.db_path = db_path
        self.alerts = []

    def run_fusion(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print("=== Iniciando Confluência V8 (Heuristic Tier Expansion) ===")

        # Cruzamento 1: Sancionado Recebendo
        # Requer que a empresa possua flags graves no BR-ACC Nacional e faturamento na base municipal
        cursor.execute('''
            SELECT c.cnpj, c.razao_social, p.total_pago, c.has_sanction, c.has_tcu_sanction, c.has_ceis_cnep
            FROM supplier_national_context c
            JOIN (
                SELECT credor_documento, SUM(valor_pago) as total_pago 
                FROM pagamentos_normalizados GROUP BY credor_documento
            ) p ON c.cnpj = p.credor_documento
            WHERE c.has_sanction = 1 OR c.has_tcu_sanction = 1 OR c.has_ceis_cnep = 1
        ''')
        rows = cursor.fetchall()
        for r in rows:
            self.alerts.append({
                "regra": "FORNECEDOR_SANCIONADO_E_RECEBENDO_MUNICIPIO",
                "tier": "T1",
                "severidade": "critica",
                "titulo": "Empresa Sancionada/Inidônea Recebendo Recursos",
                "descricao": f"O credor {r['cnpj']} ({r['razao_social']}) possui infrações federais graves no TCU/CEIS e recebeu R$ {r['total_pago']} no município.",
                "acao_auditoria": ["Verificar Certidão Negativa", "Confirmar exclusão no SICAF"],
                "evidencias": {"cnpj": r['cnpj'], "valor_recebido": r['total_pago']}
            })

        # Cruzamento 2: Desprovido de Lastro Federal operando Alto Volume Local
        cursor.execute('''
            SELECT c.cnpj, c.razao_social, p.total_pago
            FROM supplier_national_context c
            JOIN (
                SELECT credor_documento, SUM(valor_pago) as total_pago 
                FROM pagamentos_normalizados GROUP BY credor_documento
            ) p ON c.cnpj = p.credor_documento
            WHERE c.has_federal_contracts = 0 
              AND c.has_federal_transfers = 0 
              AND p.total_pago > 50000
        ''')
        rows = cursor.fetchall()
        for r in rows:
            self.alerts.append({
                "regra": "FORNECEDOR_SEM_LASTRO_FEDERAL_E_ALTO_VOLUME_LOCAL",
                "tier": "T2",
                "severidade": "media",
                "titulo": "Sem Histórico Federal e Alta Absorção Local",
                "descricao": f"A empresa {r['cnpj']} drena montantes altíssimos (R$ {r['total_pago']}) da prefeitura, mas é um 'fantasma' na base do ComprasNet e TransfereGov.",
                "acao_auditoria": ["Revisar portfólio físico da empresa e endereço de sede"],
                "evidencias": {"cnpj": r['cnpj'], "volume_captado": r['total_pago']}
            })

        # Cruzamento 3: Risco Político Latente (PEP / TSE)
        cursor.execute('''
            SELECT c.cnpj, c.razao_social, p.total_pago, c.has_pep_match, c.has_tse_donation_history
            FROM supplier_national_context c
            JOIN (
                SELECT credor_documento, SUM(valor_pago) as total_pago 
                FROM pagamentos_normalizados GROUP BY credor_documento
            ) p ON c.cnpj = p.credor_documento
            WHERE c.has_pep_match = 1 OR c.has_tse_donation_history = 1
        ''')
        rows = cursor.fetchall()
        for r in rows:
            self.alerts.append({
                "regra": "EXPOSICAO_POLITICA_FORNECEDOR",
                "tier": "T2",
                "severidade": "alta",
                "titulo": "Sócio PEP ou Histórico Eleitoral",
                "descricao": f"O fornecedor {r['cnpj']} possui laços estreitos em listas PEP (Pessoa Politicamente Exposta) ou histórico ativo CNE/TSE. Pagamento atrelado: R$ {r['total_pago']}.",
                "acao_auditoria": ["Avaliar grau de parentesco de 1/2o grau com secretariado de Tijucas"],
                "evidencias": {"cnpj": r['cnpj']}
            })

        conn.close()
        print(f"Geramos {len(self.alerts)} Alertas Multicamadas V8.")
        
    def export(self):
        filename = "alertas_hibridos_v8.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.alerts, f, ensure_ascii=False, indent=4)
        print(f"Lote exportado sob a insígnia {filename}")

if __name__ == "__main__":
    v8 = HybridFraudEngineV8(DB_PATH)
    v8.run_fusion()
    v8.export()
