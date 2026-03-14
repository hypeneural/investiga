import json
import sqlite3
import random
from typing import List
from datetime import datetime

from schemas_v7 import EmissaoEmpenho, AlertV7
from rules_v7 import (
    rule_conta_bancaria_compartilhada,
    rule_fracionamento_textual,
    rule_aditivo_precoce,
    rule_retencao_atipica
)

class FraudEngineV7:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.empenhos: List[EmissaoEmpenho] = []
        self.alerts: List[AlertV7] = []

    def _parse_date(self, d_str: str):
        if not d_str: return None
        try:
            return datetime.strptime(d_str[:10], "%d/%m/%Y").date()
        except:
            return None

    def load_data(self):
        """
        Carrega os empenhos da base de pagamentos brutos para montar o pipeline estrutural.
        Como o scraper ainda não desceu nas abas de Bancos e Histórico, injetamos mocks 
        determinísticos nestes campos para homologar os clusters textuais e Laranjas.
        """
        print(f"[{datetime.now().time()}] Injetando lote de Empenhos a partir de {self.db_path}...")
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM pagamentos_normalizados LIMIT 5000")
            rows = cursor.fetchall()
            
            # Controladores de Mocks Aleatórios (Apenas para Teste da Matemática)
            mock_contas = ["001|1234|99999-9", "104|1795|575859332-6", "341|0001|12345-6"]
            mock_historicos = [
                "Aquisicao de material de expediente para manutencao da secretaria",
                "Contratacao de empresa para reforma da escola municipal",
                "Locacao de software de gestao escolar integrada",
                "Fornecimento de merenda escolar perecivel",
                "Servico de manutencao preventiva nos veiculos da frota"
            ]
            
            for r in rows:
                raw = json.loads(r['raw_data'])
                cnpj = r['credor_documento']
                
                # Semeia aleatoriedade baseada no CNPJ para manter "Mesmo Credor = Mesmos Mocks" parcial
                seed = sum(ord(c) for c in cnpj) if cnpj else 0
                
                # Forçaremos alguns clones exatos para acionar as regras de "Fracionamento"
                h_mock = mock_historicos[seed % len(mock_historicos)]
                c_mock = mock_contas[seed % len(mock_contas)]
                
                # Forçando Anomalia de Conta Compartilhada em 5% dos casos
                if random.random() < 0.05:
                     c_mock = "104|1795|575859332-6" # Força o Laranja
                     
                val_empenho = r['valor_pago'] or 0.0
                
                # Força Retenção Atípica
                val_retido = val_empenho * 0.55 if random.random() < 0.02 else val_empenho * 0.05 
                
                # Força Aditivos Precoces
                aditivo = str(random.randint(1, 5)) if random.random() < 0.03 else None
                
                empenho = EmissaoEmpenho(
                    id_pagamento=r['id_pagamento'],
                    empenho_numero=r['empenho_numero'],
                    empenho_ano=r['empenho_ano'],
                    data_emissao=self._parse_date(r['data_pagamento']),
                    credor_cnpj=cnpj or "00.000.000/0000-00",
                    credor_nome=r['credor_nome'] or "DESCONHECIDO",
                    orgao_descricao="SECRETARIA MOCK (V7 EM DEV)",
                    unidade_descricao="FUNDO MOCK",
                    acao="ACAO PADRAO",
                    despesa="33900000",
                    modalidade="DISPENSA",
                    licitacao_numero="123/2026",
                    data_homologacao=self._parse_date(r['data_pagamento']), # Aproximado mock
                    contrato_numero=f"CT-{seed % 100}/2026",
                    aditivo_numero=aditivo,
                    historico=h_mock,
                    valor_empenho=val_empenho,
                    valor_retido=val_retido,
                    banco=c_mock.split("|")[0],
                    agencia=c_mock.split("|")[1],
                    conta=c_mock.split("|")[2],
                )
                self.empenhos.append(empenho)
            
            conn.close()
            print(f"[{datetime.now().time()}] {len(self.empenhos)} empenhos carregados/mockados com sucesso.")
            
        except Exception as e:
            print(f"Falha gravíssima ao ler SQLite: {e}")

    def run(self):
        """Pipeline Prático (Etapa 4): Rodar regras estatísticas agregadas."""
        print(f"[{datetime.now().time()}] Inicializando Agrupadores Analíticos (Clustering V7)...")
        
        self.alerts.extend(rule_conta_bancaria_compartilhada(self.empenhos))
        self.alerts.extend(rule_fracionamento_textual(self.empenhos))
        self.alerts.extend(rule_aditivo_precoce(self.empenhos))
        self.alerts.extend(rule_retencao_atipica(self.empenhos))

    def export(self, filename="alertas_fraude_v7.json"):
        payload = [a.to_dict() for a in self.alerts]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        print(f"\n[!] Motor V7 finalizou a Análise Estatística. Gerados {len(self.alerts)} Alertas Estruturais.")
        print(f" -> Arquivo exportado: {filename}\n")

if __name__ == "__main__":
    db = r"c:\Users\Usuario\.gemini\antigravity\scratch\scrapers\output_scraping\tijucas_raw.db"
    
    eng = FraudEngineV7(db_path=db)
    eng.load_data()
    eng.run()
    eng.export()
