import os
import time
import json
import uuid
import logging
import sqlite3
from datetime import datetime

# Importa o Cliente V9.1 construído anteriormente
from openrouter_client import FraudOpenRouterClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [NLP-DISPATCHER] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WORKER_ID = f"nlp-worker-{uuid.uuid4().hex[:8]}"
POLL_SECONDS = 5
DB_PATH = "../scrapers/output_scraping/tijucas_raw.db"

# ---------------------------------------------------------
# Estruturas do SQLite
# ---------------------------------------------------------

SQL_INIT_TABLES = """
CREATE TABLE IF NOT EXISTS nlp_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_type TEXT NOT NULL,
  source_id TEXT,
  cluster_hash TEXT,
  supplier_doc TEXT,
  priority INTEGER NOT NULL DEFAULT 100,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  error_type TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  locked_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expense_semantic_labels (
  source_id TEXT PRIMARY KEY,
  cluster_hash TEXT,
  categoria_primaria TEXT,
  subcategoria TEXT,
  natureza_objeto TEXT,
  grau_genericidade TEXT,
  compatibilidade_orgao_objeto TEXT,
  compatibilidade_cnae_objeto TEXT,
  red_flags_semanticas_json TEXT,
  confianca REAL,
  justificativa_curta TEXT,
  model_used TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_nlp_reviews (
  case_id TEXT PRIMARY KEY,
  prioridade TEXT,
  motivo_principal TEXT,
  resumo_auditavel TEXT,
  checklist_auditoria_json TEXT,
  model_used TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

class NlpDispatcher:
    def __init__(self, db_path, openrouter_client):
        self.db_path = db_path
        self.client = openrouter_client
        self._bootstrap_db()

    def _get_conn(self):
        # Row factory dict para facilitar manipulação
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _bootstrap_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.executescript(SQL_INIT_TABLES)
        conn.commit()
        conn.close()
        logger.info("Tabelas da Fila NLP Inicializadas.")

    def run_dispatcher(self):
        logger.info(f"== Dispatcher Iniciado ({WORKER_ID}) ==")
        while True:
            try:
                # 1. Alimenta a Fila (Engatilhar novos itens)
                self.enqueue_classify_expense_tasks()
                # self.enqueue_prioritize_case_tasks() # Ativaremos Fila B depois de termos Casos e Alertas
                
                # 2. Consome a Fila (Worker)
                self.process_queue_loop()
            except Exception as e:
                logger.error(f"Erro Crítico no Dispatcher: {e}")
                time.sleep(POLL_SECONDS)

    # ---------------------------------------------------------
    # Enfileiramento (Enqueue)
    # ---------------------------------------------------------
    def enqueue_classify_expense_tasks(self):
        """
        Adaptação da regra 'Fila A' para a realidade atual base `tijucas_raw`.
        Prioriza Clusters Únicos (Histórico) dos maiores Fornecedores.
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        # Como SQLite não tem ROW_NUMBER OVER PARTITION, 
        # Crio agrupamento simples e limito aos maiores credores
        c.execute('''
            SELECT 
                MAX(id_pagamento) as id_representante,
                credor_nome, credor_documento,
                MIN(empenho_numero) as orgao_stub,
                SUM(valor_pago) as valor_total,
                MIN(raw_data) as raw_data
            FROM pagamentos_normalizados
            WHERE raw_data IS NOT NULL
            GROUP BY credor_documento
            ORDER BY valor_total DESC
            LIMIT 100
        ''')
        
        candidatos = c.fetchall()
        inserts = 0
        
        for row in candidatos:
            try:
                payload = json.loads(row['raw_data'])
                # Parsing da base de transparência raw
                historico = payload.get("despesa", "Historico Nao Identificado")
                
                if len(historico.strip()) < 20: 
                    continue # Ignora histórico inútil
                    
                import hashlib
                cluster_hash = hashlib.sha256(historico.encode('utf-8')).hexdigest()
                
                # Checa se este cluster já está na fila
                c.execute("SELECT 1 FROM nlp_queue WHERE cluster_hash = ? AND task_type = 'classify_expense'", (cluster_hash,))
                if c.fetchone(): continue
                
                # Prepara o JSON (Tarefa A)
                json_to_llm = {
                    "orgao": payload.get("entidade", "N/A"),
                    "unidade": "N/A", # Tijucas API omite na listagem base
                    "acao": payload.get("recurso", "N/A"),
                    "despesa": "N/A", 
                    "modalidade": "N/A", 
                    "historico": historico,
                    "credor_nome": row['credor_nome'],
                    "cnae": "Busca Pendente do BR-ACC" 
                }
                
                # Regra de Prioridade: Top Valor Pago => Prioridade Menor (10 a 50)
                priority = max(10, 100 - int(row['valor_total'] / 10000))
                
                c.execute('''
                    INSERT INTO nlp_queue (task_type, source_id, cluster_hash, supplier_doc, priority, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('classify_expense', row['id_representante'], cluster_hash, row['credor_documento'], priority, json.dumps(json_to_llm)))
                
                inserts += 1

            except Exception as e:
                logger.error(f"Erro inserindo fila: {e}")
                
        if inserts > 0:
            logger.info(f"Enfileirou +{inserts} clusters únicos para CLASSIFY_EXPENSE")
            
        conn.commit()
        conn.close()

    # ---------------------------------------------------------
    # Worker Execução
    # ---------------------------------------------------------
    def process_queue_loop(self):
        """Consume 1 Job por vez (Worker Unitário Limitado para não estourar rate-limits)"""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Pega o próximo
        c.execute('''
            SELECT * FROM nlp_queue
            WHERE status = 'queued' OR status = 'provider_error'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        ''')
        job = c.fetchone()
        
        if not job:
            conn.close()
            time.sleep(POLL_SECONDS)
            return

        job_id = job['id']
        task_type = job['task_type']
        
        # Lock Job
        c.execute("UPDATE nlp_queue SET status = 'processing', locked_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
        conn.commit()
        
        try:
            payload_json = json.loads(job['payload_json'])
            
            if task_type == 'classify_expense':
                logger.info(f"Processando NLP [CLASSIFY_EXPENSE] -> Fatura: {job['source_id']}")
                result = self.client.classify_expense(**payload_json)
                self._handle_result(conn, c, job, result)
                
            elif task_type == 'prioritize_audit_case':
                logger.info(f"Processando NLP [PRIORITIZE] -> Caso: {job['source_id']}")
                result = self.client.prioritize_audit_case(payload_json)
                self._handle_result(conn, c, job, result)
            else:
                c.execute("UPDATE nlp_queue SET status = 'failed', error_type = 'unknown_task' WHERE id = ?", (job_id,))
                
        except Exception as e:
            logger.error(f"Exceção fatal no NLP Worker Job {job_id}: {e}")
            c.execute("UPDATE nlp_queue SET status = 'failed', error_type = 'worker_exception' WHERE id = ?", (job_id,))
            
        conn.commit()
        conn.close()
        # Rate Limit Sleep (A pedido do usuário, intervalo calmo entre queries)
        time.sleep(3)

    # ---------------------------------------------------------
    # Tratamento de Retornos
    # ---------------------------------------------------------
    def _handle_result(self, conn, cursor, job, result):
        status = result["status"]
        job_id = job['id']
        
        if status == "success":
            cursor.execute("UPDATE nlp_queue SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
            
            # Persistir saida no dominio
            data = result["data"]
            model = result["metadata"]["model_used"]
            
            if job['task_type'] == 'classify_expense':
                cursor.execute('''
                    INSERT OR REPLACE INTO expense_semantic_labels
                    (source_id, cluster_hash, categoria_primaria, subcategoria, natureza_objeto, 
                     grau_genericidade, compatibilidade_orgao_objeto, compatibilidade_cnae_objeto,
                     red_flags_semanticas_json, confianca, justificativa_curta, model_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job['source_id'], job['cluster_hash'],
                    data.get('categoria_primaria'), data.get('subcategoria'), data.get('natureza_objeto'),
                    data.get('grau_genericidade'), data.get('compatibilidade_orgao_objeto'), data.get('compatibilidade_cnae_objeto'),
                    json.dumps(data.get('red_flags_semanticas', [])), data.get('confianca'), data.get('justificativa_curta'),
                    model
                ))
            return

        retry_count = job['retry_count']
        
        if status in ("provider_error", "json_parse_error"):
            if retry_count < 2:
                # Requeue
                cursor.execute("UPDATE nlp_queue SET status = 'queued', retry_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (retry_count + 1, job_id))
            else:
                cursor.execute("UPDATE nlp_queue SET status = 'manual_review', error_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, job_id))
            return

        # Fatal / Schema Error
        cursor.execute("UPDATE nlp_queue SET status = 'manual_review', error_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, job_id))

if __name__ == "__main__":
    dummy_key = "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"
    client = FraudOpenRouterClient(api_key=dummy_key, db_path="nlp_cache.db")
    dispatcher = NlpDispatcher(db_path=DB_PATH, openrouter_client=client)
    logger.info("Sistema armado. Iniciando Fila NLP Lenta (Foco em Top 100 Fornecedores).")
    
    # Roda o Worker Indefinidamente (Intervalo cravado em POLL_SECONDS na classe)
    dispatcher.run_dispatcher()
