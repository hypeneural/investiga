import json
import requests
import sqlite3
import time
import os
from pathlib import Path

BASE_PAGE = "https://tijucas.atende.net/transparencia/item/embed/data/eyJjb2RpZ28iOiIzIiwidGlwbyI6IjEiLCJncnVwbyI6IjMifQ==/item/pagamentos"
LIST_URL = "https://tijucas.atende.net/transparencia/item/embed/data/eyJjb2RpZ28iOiIzIiwidGlwbyI6IjEiLCJncnVwbyI6IjMifQ==/item/atende.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://tijucas.atende.net",
    "Referer": BASE_PAGE,
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

class TijucasScraper:
    def __init__(self, db_path="tijucas_raw.db"):
        self.db_path = db_path
        self.session = self._make_session()
        self._setup_db()

    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS page_responses (
                pagina INTEGER PRIMARY KEY,
                raw_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagamentos_normalizados (
                id_pagamento TEXT PRIMARY KEY,
                credor_nome TEXT,
                credor_documento TEXT,
                data_pagamento TEXT,
                valor_pago REAL,
                empenho_numero TEXT,
                empenho_ano TEXT,
                liquidacao_sequencia TEXT,
                tipo_pessoa TEXT,
                ordem_compra_numero TEXT,
                ordem_compra_ano TEXT,
                raw_data TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _make_session(self):
        s = requests.Session()
        s.headers.update(HEADERS)
        print("Injetando cookies manuais da sessão capturada...")
        
        # O cookie avisosPortal precisa ser uma string, não um dicionário codificado de novo se formos usar set. O Requests faz isso seguro via dict.
        cookies_dict = {
            "_ga": "GA1.1.673045497.1771090313",
            "_ga_KXJ6JS10JQ": "GS2.1.s1773453310$o18$g1$t1773456639$j20$l0$h0",
            "solicitarCaptcha": "0",
            "cidade": "padrao",
            "avisosPortal": '{"2030":{"WAU":["1"]}}',
            "PHPSESSID": "vi7h7qeknqbiicsil80lcphont"
        }
        
        requests.utils.add_dict_to_cookiejar(s.cookies, cookies_dict)
        return s

    def _parse_maybe_json(self, resp):
        resp.encoding = "iso-8859-1"
        text = resp.text.strip()
        try:
            return json.loads(text)
        except Exception:
            return text

    def fetch_page(self, pagina=1, registros=50, max_retries=3):
        params = {
            "rot": "45094",
            "aca": "101",
            "ajax": "t",
            "processo": "processaDados",
            "ajaxPrevent": str(int(time.time() * 1000)),
        }
        
        
        parametro_json = json.dumps({
            "__order_consulta_padrao": [
                {"order": "pagdata", "orderT": "desc", "tipo": 1},
                {"order": "pagnumero", "orderT": "desc", "tipo": 1}
            ]
        })
        
        payload = {
            "registros": str(registros),
            "pagina": str(pagina),
            "selecionar": "false",
            "contaRegistros": "true",
            "totalizaRegistros": "false",
            "nivelArvore": "null",
            "parametro": parametro_json
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                r = self.session.post(LIST_URL, params=params, data=payload, timeout=30)
                r.raise_for_status()
                data = self._parse_maybe_json(r)
                if isinstance(data, dict):
                    return data
                else:
                    print(f"[!] Aviso: Resposta não é JSON na página {pagina}.")
                    return None
            except Exception as e:
                print(f"[!] Erro na página {pagina} (Tentativa {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(2 * attempt)
        return None

    def normalize_payment(self, item):
        try:
            id_pag = f"{item.get('pagnumero')}|{item.get('empnro')}|{item.get('empsub')}|{item.get('loaano')}|{item.get('liqsequencia')}|{item.get('liqtipo')}|{item.get('ano_liquidacao')}"
            
            valor_pago = item.get('pagvalor', 0)
            if isinstance(valor_pago, str):
                valor_pago = float(valor_pago.replace('.', '').replace(',', '.'))
            
            return {
                "id_pagamento": id_pag,
                "credor_nome": item.get('uninomerazao', ''),
                "credor_documento": item.get('unicpfcnpj', ''),
                "data_pagamento": item.get('pagdata', ''),
                "valor_pago": float(valor_pago),
                "empenho_numero": item.get('empnro', ''),
                "empenho_ano": item.get('loaano', ''),
                "liquidacao_sequencia": item.get('liqsequencia', ''),
                "tipo_pessoa": str(item.get('unitipo', '')),
                "ordem_compra_numero": item.get('copnro', ''),
                "ordem_compra_ano": item.get('copano', ''),
                "raw_data": json.dumps(item)
            }
        except Exception as e:
            print(f"[!] Erro ao normalizar item: {e}")
            return None

    def run_scraper(self, start_page=1, limit_pages=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        pagina = start_page
        registros_por_pagina = 50
        total_paginas = limit_pages if limit_pages else 1 
        
        print("\n=== Iniciando Raspagem ===")
        while pagina <= total_paginas:
            print(f"Buscando página {pagina} / {total_paginas if total_paginas > 1 else '?'}...")
            
            cursor.execute("SELECT raw_json FROM page_responses WHERE pagina = ?", (pagina,))
            row = cursor.fetchone()
            if row and not limit_pages:
                if pagina == 1:
                    try:
                        saved_data = json.loads(row[0])
                        if "paginas" in saved_data:
                            total_paginas = int(saved_data["paginas"])
                        elif "total" in saved_data:
                            import math
                            total_paginas = math.ceil(int(saved_data["total"]) / registros_por_pagina)
                        print(f" -> Página 1 já no banco. Recuperado teto de {total_paginas} páginas do cache.")
                    except:
                        pass
                else:
                    print(f" -> Página {pagina} já existe no banco. Pulando.")
                    
                pagina += 1
                continue
                
            data = self.fetch_page(pagina=pagina, registros=registros_por_pagina)
            
            if not data:
                print(" -> [!!!] Falha persistente ao obter dados. Interrompendo loop principal.")
                break
                
            cursor.execute(
                "INSERT OR REPLACE INTO page_responses (pagina, raw_json) VALUES (?, ?)", 
                (pagina, json.dumps(data))
            )
            
            if "paginas" in data and not limit_pages:
                total_paginas = int(data["paginas"])
            elif "total" in data and not limit_pages:
                total_registros = int(data["total"])
                import math
                total_paginas = math.ceil(total_registros / registros_por_pagina)
                 
            if "dados" in data and isinstance(data["dados"], list):
                items_brutos = data["dados"]
                print(f" -> {len(items_brutos)} registros encontrados.")
                
                inserts = 0
                for registro in items_brutos:
                    # No novo json, os dados em si estão aninhados sob "valor"
                    item = registro.get("valor", {})
                    if not item:
                        continue
                        
                    norm = self.normalize_payment(item)
                    if norm:
                        cursor.execute('''
                            INSERT OR REPLACE INTO pagamentos_normalizados
                            (id_pagamento, credor_nome, credor_documento, data_pagamento, valor_pago,
                             empenho_numero, empenho_ano, liquidacao_sequencia, tipo_pessoa,
                             ordem_compra_numero, ordem_compra_ano, raw_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            norm["id_pagamento"], norm["credor_nome"], norm["credor_documento"],
                            norm["data_pagamento"], norm["valor_pago"], norm["empenho_numero"],
                            norm["empenho_ano"], norm["liquidacao_sequencia"], norm["tipo_pessoa"],
                            norm["ordem_compra_numero"], norm["ordem_compra_ano"], norm["raw_data"]
                        ))
                        inserts += 1
                conn.commit()
                print(f" -> {inserts} registros salvos no banco de dados normalizado.")
            
            pagina += 1
            time.sleep(1.5)
            
        conn.close()
        print("=== Raspagem Concluída ===")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="tijucas_raw.db", help="Caminho para o banco SQLite")
    parser.add_argument("--test", action="store_true", help="Baixa apenas 2 páginas para teste")
    args = parser.parse_args()
    
    out_dir = Path("output_scraping")
    out_dir.mkdir(exist_ok=True)
    db_file = out_dir / args.db
    
    scraper = TijucasScraper(str(db_file))
    limit = 2 if args.test else None
    scraper.run_scraper(limit_pages=limit)
