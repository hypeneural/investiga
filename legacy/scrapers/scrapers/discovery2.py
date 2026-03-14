from playwright.sync_api import sync_playwright
import time
import json
from urllib.parse import parse_qsl

def run():
    print("Iniciando discovery via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        intercepted = []
        def handle_request(req):
            if req.method == "POST" and "atende.php" in req.url:
                intercepted.append({"url": req.url, "data": req.post_data})
        
        page.on("request", handle_request)
        
        url = "https://tijucas.atende.net/transparencia/item/embed/data/eyJjb2RpZ28iOiIzIiwidGlwbyI6IjEiLCJncnVwbyI6IjMifQ==/item/pagamentos"
        page.goto(url, wait_until="networkidle")
        time.sleep(2)
        # Wait explicitly for the data POST
        with page.expect_response(lambda response: "processaDados" in response.url, timeout=30000):
            page.locator("text='Consultar'").nth(0).click()
        
        print("Dados retornados pelo servidor. Renderizando DOM...")
        time.sleep(3)
        
        print("Tirando screenshot da grid cheia...")
        page.screenshot(path="grid_loaded.png", full_page=True)
        
        lupas = page.locator("i.fa-search, [title*='Visualizar'], [title*='Detalhes']")
        if lupas.count() > 0:
            print(f"Encontradas {lupas.count()} lupas. Clicando na primeira...")
            lupas.nth(0).click()
            time.sleep(5)
        else:
            print("Não achou lupa. Tentando duplo clique na linha de dados tr_0...")
            trs = page.locator("tr[id^='tr_']")
            if trs.count() > 0:
                print(f"Encontradas {trs.count()} linhas de dados válidas! Texto da primeira:")
                print(trs.nth(0).inner_text().strip()[:100])
                trs.nth(0).dblclick()
                
                # Aguardamos explicitamente o request montaTela para o detalhe
                try:
                    with page.expect_response(lambda r: "aca=105" in r.url, timeout=10000):
                        pass
                except:
                    print("Timeout esperando action 105. Verifique os logs.")
            else:
                print("ERRO CRITICO: Nenhuma linha tr_X encontrada. A grid falhou ao renderizar.")
                
        print("\n--- ANALISANDO REQUISIÇÕES INTERCEPTADAS ---")
        relevantes = []
        for req in intercepted:
            if "aca=105" in req['url'] or "selecionar=true" in req['url'] or "rot=37152" in req['url']:
                try:
                    pd = req['data']
                    parsed = dict(parse_qsl(pd)) if pd else pd
                    relevantes.append({
                        "url": req['url'],
                        "payload": parsed
                    })
                except:
                    relevantes.append({"url": req['url'], "payload": req['data']})
                    
        with open("relevantes.json", "w", encoding="utf-8") as f:
            json.dump(relevantes, f, indent=2)
        print(f"Salvos {len(relevantes)} requests relevantes em relevantes.json")
                
        browser.close()

if __name__ == "__main__":
    run()
