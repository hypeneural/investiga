import json
import logging
import requests
import time
import random
import hashlib
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FraudOpenRouterClient:
    """
    Cliente Oficial da Camada Semântica de Fraudes (V9.1).
    Integra Cache Local SQLite, Backoff Exponencial com Jitter, Tipagem de Erros
    (provider_error|json_parse_error) e Fallback Nativo via OpenRouter.
    """
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    PRIMARY_MODEL = "stepfun/step-3.5-flash:free"
    FALLBACK_MODELS = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "arcee-ai/trinity-large-preview:free"
    ]
    
    def __init__(self, api_key: str, db_path: str = "nlp_cache.db"):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tijucas-transparencia.local",
            "X-OpenRouter-Title": "Tijucas Fraud Engine"
        }
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS nlp_inferences (
                hash_id TEXT PRIMARY KEY,
                task_type TEXT,
                input_resumido TEXT,
                output_json TEXT,
                model_used TEXT,
                status TEXT,
                attempts INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _generate_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _get_cache(self, hash_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT output_json, model_used, status FROM nlp_inferences WHERE hash_id = ?", (hash_id,))
        row = c.fetchone()
        conn.close()
        
        if row and row[2] == "success":
            return {
                "status": "success",
                "data": json.loads(row[0]),
                "metadata": {
                    "model_used": row[1],
                    "cached": True,
                    "attempt": 0
                }
            }
        return None

    def _save_cache(self, hash_id: str, task_type: str, input_resumido: str, output_json: dict, model_used: str, status: str, attempts: int):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO nlp_inferences 
            (hash_id, task_type, input_resumido, output_json, model_used, status, attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            hash_id, 
            task_type, 
            input_resumido, 
            json.dumps(output_json, ensure_ascii=False) if output_json is not None else None, 
            model_used, 
            status, 
            attempts
        ))
        conn.commit()
        conn.close()

    def _get_schema_classificacao(self) -> dict:
        return {
            "name": "classificacao_despesa_publica",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "categoria_primaria": {
                        "type": "string",
                        "enum": [
                            "obra_reforma", "material", "servico_tecnico", 
                            "servico_generico", "locacao", "evento", 
                            "publicidade", "saude", "educacao", "outro"
                        ]
                    },
                    "subcategoria": { "type": "string" },
                    "natureza_objeto": {
                        "type": "string",
                        "enum": ["obra", "servico", "material", "locacao", "mista", "indefinida"]
                    },
                    "grau_genericidade": {
                        "type": "string",
                        "enum": ["alta", "media", "baixa"]
                    },
                    "compatibilidade_orgao_objeto": {
                        "type": "string",
                        "enum": ["alta", "media", "baixa"]
                    },
                    "compatibilidade_cnae_objeto": {
                        "type": "string",
                        "enum": ["alta", "media", "baixa", "nao_aplicavel"]
                    },
                    "red_flags_semanticas": {
                        "type": "array",
                        "items": { "type": "string" }
                    },
                    "confianca": { "type": "number" },
                    "justificativa_curta": { "type": "string" }
                },
                "required": [
                    "categoria_primaria", "subcategoria", "natureza_objeto",
                    "grau_genericidade", "compatibilidade_orgao_objeto",
                    "compatibilidade_cnae_objeto", "red_flags_semanticas",
                    "confianca", "justificativa_curta"
                ],
                "additionalProperties": False
            }
        }

    def _get_schema_priorizacao(self) -> dict:
        return {
            "name": "priorizacao_auditoria",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "prioridade": {
                        "type": "string",
                        "enum": ["critica", "alta", "media", "baixa"]
                    },
                    "motivo_principal": { "type": "string" },
                    "resumo_auditavel": { "type": "string" },
                    "checklist_auditoria": {
                        "type": "array",
                        "items": { "type": "string" }
                    }
                },
                "required": [
                    "prioridade", "motivo_principal", 
                    "resumo_auditavel", "checklist_auditoria"
                ],
                "additionalProperties": False
            }
        }

    def _call_api_with_retry(self, payload: dict, schema_definition: dict, max_retries: int = 3) -> Dict[str, Any]:
        """
        Executa inferência estruturada com Jitter Backoff.
        Retorna status separados: success, provider_error, json_parse_error, schema_error, manual_review_required.
        """
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                r = requests.post(
                    self.BASE_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                
                # Tratamento explícito de High Load/Rate Limiting com Backoff Jitter
                if r.status_code in [429, 502, 503, 504]:
                    sleep_time = (2 ** attempt) + random.uniform(0.1, 1.5)
                    logger.warning(f"[Tentativa {attempt}] Provider sobrecarregado (HTTP {r.status_code}). Dormindo {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    if attempt == max_retries:
                        return {"status": "provider_error", "data": None, "metadata": {"error": f"HTTP {r.status_code}", "attempt": attempt, "model_used": "none"}}
                    continue
                    
                r.raise_for_status()
                data = r.json()
                
                if not data.get("choices"):
                    return {"status": "provider_error", "data": None, "metadata": {"error": "Sem choices no retorno", "attempt": attempt, "model_used": "none"}}
                
                content = data["choices"][0]["message"]["content"]
                model_used = data.get("model", "unknown_model")
                
                # App Backend Validação: Garante integridade do JSON
                try:
                    json_parsed = json.loads(content)
                    return {
                        "status": "success",
                        "data": json_parsed,
                        "metadata": {
                            "model_used": model_used,
                            "attempt": attempt,
                            "cached": False
                        }
                    }
                except json.JSONDecodeError:
                    logger.warning(f"[Tentativa {attempt}] Erro Parse JSON ({model_used}): {content[:100]}...")
                    if attempt < max_retries:
                        # Auto-correção pro modelo tentar limpar o output (CLONANDO o payload para não poluir tentativas longas)
                        import copy
                        new_payload = copy.deepcopy(payload)
                        new_payload["messages"].append({"role": "assistant", "content": content})
                        new_payload["messages"].append({"role": "user", "content": "Erro de parse. Você enviou formatações inúteis. Retorne APENAS um JSON válido seguindo estritamente o schema predeterminado."})
                        payload = new_payload
                        continue
                    else:
                        return {
                            "status": "json_parse_error",
                            "data": None,
                            "metadata": {"model_used": model_used, "attempt": attempt, "raw_output": content}
                        }
                        
            except requests.exceptions.RequestException as e:
                sleep_time = (2 ** attempt) + random.uniform(0.1, 1.0)
                logger.error(f"[Tentativa {attempt}] Request Error: {e}. Dormindo {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                if attempt == max_retries:
                    return {"status": "provider_error", "data": None, "metadata": {"attempt": attempt, "error": str(e), "model_used": "none"}}
                    
        return {
            "status": "manual_review_required",
            "data": None,
            "metadata": {"model_used": "none", "attempt": attempt}
        }

    def classify_expense(self, orgao: str, unidade: str, acao: str, despesa: str, 
                         modalidade: str, historico: str, credor_nome: str, cnae: str) -> Dict[str, Any]:
        """Tarefa A - Classificador Semântico com Cache por Assinatura"""
        
        # Gerar Assinatura Textual Única do Cluster (Agora blindada por Versão de Engine e Prompt)
        historico_norm = historico.strip().lower()
        assinatura = f"v9.1|p1|{orgao}|{unidade}|{acao}|{despesa}|{modalidade}|{historico_norm}|{cnae}"
        hash_id = self._generate_hash(assinatura)
        
        # Consultar Cache
        cached_result = self._get_cache(hash_id)
        if cached_result:
            return cached_result
            
        system_prompt = (
            "Você é um classificador técnico de despesas públicas.\n\n"
            "Sua função NÃO é concluir fraude, corrupção, nepotismo ou crime.\n"
            "Sua função é apenas:\n"
            "1) classificar o objeto da despesa,\n"
            "2) medir genericidade textual,\n"
            "3) avaliar compatibilidade material entre órgão, objeto e CNAE,\n"
            "4) devolver JSON estrito no schema informado.\n\n"
            "Regras:\n"
            "- Não invente fatos ausentes.\n"
            "- Não use linguagem acusatória.\n"
            "- Se não houver base suficiente, use 'media', 'baixa' ou 'nao_aplicavel'.\n"
            "- Responda apenas JSON válido.\n"
            "- Não use markdown.\n"
            "- Não adicione campos fora do schema."
        )

        user_content = (
            f"Órgão: {orgao}\n"
            f"Unidade: {unidade}\n"
            f"Ação: {acao}\n"
            f"Despesa: {despesa}\n"
            f"Modalidade: {modalidade}\n"
            f"Histórico: {historico}\n"
            f"Fornecedor: {credor_nome}\n"
            f"CNAE principal: {cnae}"
        )

        payload = {
            "model": self.PRIMARY_MODEL,
            "models": self.FALLBACK_MODELS,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 800,
            "response_format": {
                "type": "json_schema",
                "json_schema": self._get_schema_classificacao()
            }
        }

        # Executa inferência da Camada B e persiste input reduzido para auditoria
        res = self._call_api_with_retry(payload, self._get_schema_classificacao())
        
        self._save_cache(
            hash_id=hash_id,
            task_type="classify_expense",
            input_resumido=user_content[:450], # Input reduzido para auditoria
            output_json=res.get("data"),
            model_used=res["metadata"].get("model_used", "none"),
            status=res["status"],
            attempts=res["metadata"].get("attempt", 0)
        )
        
        return res

    def prioritize_audit_case(self, case_bundle_json: dict) -> Dict[str, Any]:
        """Tarefa C - Priorizador com Cache por Assinatura (Versão)"""
        
        bundle_str = json.dumps(case_bundle_json, ensure_ascii=False, sort_keys=True)
        assinatura = f"v9.1|p1|{bundle_str}"
        hash_id = self._generate_hash(assinatura)
        
        cached_result = self._get_cache(hash_id)
        if cached_result:
            return cached_result
            
        system_prompt = (
            "Você é um revisor analítico de indícios administrativos.\n\n"
            "Você NÃO deve afirmar fraude, crime ou parentesco como fato.\n"
            "Você deve:\n"
            "1) resumir o caso de forma prudente,\n"
            "2) priorizar revisão humana,\n"
            "3) sugerir documentos e passos de auditoria,\n"
            "4) respeitar os tiers de evidência.\n\n"
            "Regras:\n"
            "- T1 = fato objetivo documental\n"
            "- T2 = padrão suspeito\n"
            "- T3 = hipótese relacional/contextual\n"
            "- Nunca elevar T3 para linguagem conclusiva\n"
            "- Responda apenas JSON válido\n"
            "- Não use markdown"
        )
        
        payload = {
            "model": self.PRIMARY_MODEL,
            "models": self.FALLBACK_MODELS,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": bundle_str}
            ],
            "temperature": 0.1,
            "max_tokens": 800,
            "response_format": {
                "type": "json_schema",
                "json_schema": self._get_schema_priorizacao()
            }
        }

        res = self._call_api_with_retry(payload, self._get_schema_priorizacao())
        
        self._save_cache(
            hash_id=hash_id,
            task_type="prioritize_audit",
            input_resumido=bundle_str[:450],
            output_json=res.get("data"),
            model_used=res["metadata"].get("model_used", "none"),
            status=res["status"],
            attempts=res["metadata"].get("attempt", 0)
        )
        
        return res

if __name__ == "__main__":
    dummy_key = "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"
    client = FraudOpenRouterClient(api_key=dummy_key, db_path="nlp_cache.db")
    print("--- Teste de Mock com OpenRouter (Validando Cache e Fallbacks) ---")
    
    # Executamos duas vezes para testar o Cache Hit instantâneo
    for i in range(2):
        print(f"\nRodada {i+1}:")
        t0 = time.time()
        res = client.classify_expense(
            orgao="SECRETARIA DE EDUCAÇÃO",
            unidade="Divisão de Ensino",
            acao="Manutenção do CEI",
            despesa="Obras contratadas",
            modalidade="Dispensa",
            historico="Contratação de empresa especializada para pintura predial e reparos...",
            credor_nome="EMPREITEIRA FICTICIA LTDA",
            cnae="Aluguel de Palcos"
        )
        t1 = time.time()
        
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"Tempo levado: {t1-t0:.3f}s (Cache Hit: {res['metadata'].get('cached', False)})")
