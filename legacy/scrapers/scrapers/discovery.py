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
        time.sleep(4)
        print("Página carregada.")
        
        # Dumpar HTML das primeiras linhas para análise
        print("Buscando a grid...")
        html = page.evaluate("() => { const el = document.querySelector('.grid-body') || document.querySelector('table'); return el ? el.innerHTML : 'Not found'; }")
        
        with open("grid_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML da grid salvo em grid_dump.html")
        
        # Simular cliques
        rows = page.locator("tr")
        if rows.count() > 0:
            print(f"Clicando na primeira de {rows.count()} linhas...")
            try:
                # O IPM usa data-row ou algo similar. Tentar um click simples
                rows.nth(1).click()
                time.sleep(2)
                # Tentar duplo clique que geralmente abre "Visualizar"
                rows.nth(1).dblclick()
                time.sleep(4)
            except Exception as e:
                print(f"Erro no clique: {e}")
                
        print("\n--- ANALISANDO REQUISIÇÕES INTERCEPTADAS ---")
        for req in intercepted[-10:]: # Ultimas 10
            print(f"\nURL: {req['url']}")
            try:
                pd = req['data']
                parsed = dict(parse_qsl(pd)) if pd else {}
                if parsed:
                    print(json.dumps(parsed, indent=2)[:500])
                else:
                    print(req['data'])
            except:
                pass
                
        browser.close()

if __name__ == "__main__":
    run()
