from playwright.sync_api import sync_playwright
import time

def get_cookies():
    with sync_playwright() as p:
        print("Launching playwright...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        url = "https://tijucas.atende.net/transparencia/item/embed/data/eyJjb2RpZ28iOiIzIiwidGlwbyI6IjEiLCJncnVwbyI6IjMifQ==/item/pagamentos"
        print(f"Navegando para {url}")
        
        response = page.goto(url, wait_until="networkidle")
        print(f"Status: {response.status if response else 'None'}")
        
        time.sleep(3)
        cookies = context.cookies()
        print(f"Cookies obtidos: {len(cookies)}")
        for c in cookies:
            print(f"  {c['name']} = {c['value']}")
            
        browser.close()

if __name__ == "__main__":
    get_cookies()
