import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        requests = []
        async def on_response(response):
            # Only intercept JSON responses
            if "json" in response.headers.get("content-type", "") or "api" in response.url.lower():
                try:
                    resp_json = await response.json()
                    requests.append({
                        "url": response.url,
                        "method": response.request.method,
                        "status": response.status,
                        "data": resp_json
                    })
                except Exception:
                    pass
        
        page.on("response", on_response)
        
        print("Navigating to despesas page...")
        await page.goto("https://tijucas.atende.net/transparencia/item/despesas-publicas")
        await page.wait_for_timeout(12000) # give it time to load the tables
        
        with open("network_log.json", "w", encoding="utf-8") as f:
            json.dump(requests, f, indent=2, ensure_ascii=False)
            
        print(f"Logged {len(requests)} JSON/API responses.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
