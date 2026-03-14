import json
import requests
import sqlite3
import time
from pathlib import Path

# Headers e Cookies re-utilizados do scraper principal
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://tijucas.atende.net",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

class TijucasDetailScraper:
    def __init__(self, db_path="tijucas_raw.db"):
        self.db_path = db_path
        self.session = self._make_session()
        self._setup_db()

    def _make_session(self):
        s = requests.Session()
        s.headers.update(HEADERS)
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

    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detalhes_liquidacao (
                id_pagamento TEXT PRIMARY KEY,
                dados_html TEXT,
                dados_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _parse_maybe_json(self, resp):
        resp.encoding = "iso-8859-1"
        text = resp.text.strip()
        try:
            return json.loads(text)
        except Exception:
            return text

    # O Endpoint real do detalhe documentado
    def fetch_detail(self, item_row):
        url = "https://tijucas.atende.net/transparencia/item/embed/data/eyJjb2RpZ28iOiIzIiwidGlwbyI6IjEiLCJncnVwbyI6IjMifQ==/item/atende.php"
        query_params = {
            "rot": "37152",
            "aca": "101",
            "ajax": "t",
            "processo": "processaDados",
            "ajaxPrevent": str(int(time.time() * 1000)),
            "registros": "0",
            "pagina": "0",
            "selecionar": "false",
            "contaRegistros": "true",
            "totalizaRegistros": "false",
            "nivelArvore": "null"
        }
        
        # Extrair dados cruza do item base para recompor a chave perfeitamente
        raw_item = json.loads(item_row['raw_data'])

        # O segredo do IPM: O state todo vai serializado na variável "chave"
        chave_json = json.dumps({
            "clicodigo": "2030",
            "pagnumero": int(raw_item.get('pagnumero') or 0),
            "pagtipoemp": int(raw_item.get('pagtipoemp') or 2), 
            "loaano": int(raw_item.get('loaano') or 0),
            "empnro": int(raw_item.get('empnro') or 0),
            "empsub": int(raw_item.get('empsub') or 0),
            "liqsequencia": int(raw_item.get('liqsequencia') or 0),
            "liqtipo": int(raw_item.get('liqtipo') or 1),
            "ano_liquidacao": int(raw_item.get('ano_liquidacao') or raw_item.get('loaano') or 0),
            "pagloaano": int(raw_item.get('pagloaano') or raw_item.get('loaano') or 0)
        })
        
        parametro_json = json.dumps({
            "isPortal": True,
            "telaConsultaEstorno": True,
            "codigoRotinaCaller": False,
            "anonimizarNomePessoaFisica": False,
            "anonimizarCpfPessoaFisica": False,
            "grupo": "3",
            "item": "3",
            "tipo": "1",
            "janelaAutoId": "1",
            "selecionar": False,
            "selecionar_multipla": False,
            "permiteAcaoSelecionar": False,
            "anonimizarNomeRazao": None,
            "anonimizarCpfCnpj": None,
            "__identificadores": [],
            "__filtros_consulta_liquidacao_documentos_fiscais": [],
            "__order_consulta_liquidacao_documentos_fiscais": [{"order": "sequencia", "orderT": "desc", "tipo": 1}],
            "nome_consulta": "consulta_liquidacao_documentos_fiscais",
            "campos_consulta": ["Loa.ano", "Liquidacao.dataLiquidacao", "Liquidacao.sequencia", "sequenciaDocumento", "numeroDocumento", "serieDocumento", "tipoDocumento", "credor", "cpfCnpj", "Liquidacao.codigoCliente", "sequencia", "tipoLiquidacao", "dataDocumento", "tipoServicoPrestado", "Liquidacao.tipoLiquidacao", "tipoDocumentoTribunalContas", "Liquidacao.Empenho.nro", "Liquidacao.Empenho.Loa.ano", "valorDocumento", "situacao", "chaveDanfe", "Liquidacao.historico", "Liquidacao.historicoLiquidacao", "Liquidacao.Empenho.historico", "Liquidacao.Empenho.historicoEmpenho", "historico", "historicoDespesa"],
            "dados_agrupador": []
        })

        data_payload = {
            "chave": chave_json,
            "caller": "null",
            "parametro": parametro_json,
            "autoId": "1",
            "monitor": "0",
            "flush": "0",
            "ip": "168.90.121.131",
            "versaoSistema": "v2",
            "portalTransparencia": "true"
        }
        
        try:
            r = self.session.post(url, params=query_params, data=data_payload, timeout=20)
            r.raise_for_status()
            return self._parse_maybe_json(r)
        except Exception as e:
            print(f"[!] Erro ao buscar detalhe {item_row.get('id_pagamento')}: {e}")
            return None

    def run_enrichment(self, limite=5):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Selecionar itens que ainda não temos detalhe, priorizando OS MAIS RECENTES (2024)
        # O Atende.net costuma falhar com EST-000049 em empenhos muito antigos (2014/2015)
        # onde as notas fiscais não foram digitalizadas ou o cookie restringe a sessão
        cursor.execute('''
            SELECT * FROM pagamentos_normalizados
            WHERE id_pagamento NOT IN (SELECT id_pagamento FROM detalhes_liquidacao)
            ORDER BY data_pagamento DESC
            LIMIT ?
        ''', (limite,))
        
        rows = cursor.fetchall()
        print(f"Iniciando enriquecimento de {len(rows)} pagamentos...")
        
        for row in rows:
            item = dict(row)
            print(f" -> Buscando detalhe do pagamento {item['id_pagamento']}")
            
            detail_response = self.fetch_detail(item)
            if detail_response:
                # O atende.net costuma retornar um JSON que contém HTML renderizado dentro de uma chave "html" 
                # ou componentes do formulário. Vamos salvar raw.
                is_json = isinstance(detail_response, dict)
                raw_json = json.dumps(detail_response) if is_json else None
                html_resp = detail_response if not is_json else detail_response.get("html", "")
                
                cursor.execute('''
                    INSERT OR REPLACE INTO detalhes_liquidacao (id_pagamento, dados_html, dados_json)
                    VALUES (?, ?, ?)
                ''', (item['id_pagamento'], str(html_resp), raw_json))
                conn.commit()
                print("    ✓ Salvo.")
            
            time.sleep(1.2) # Respeitando os limites do servidor
            
        conn.close()
        print("Enriquecimento Concluído.")

if __name__ == "__main__":
    out_dir = Path("output_scraping")
    db_file = out_dir / "tijucas_raw.db"
    
    scraper = TijucasDetailScraper(str(db_file))
    scraper.run_enrichment(limite=3)
