import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        requests = []
        async def on_response(response):
            try:
                content_type = response.headers.get("content-type", "")
                if "image" not in content_type and "css" not in content_type and "javascript" not in content_type:
                    requests.append({
                        "url": response.url,
                        "status": response.status,
                        "type": content_type
                    })
            except Exception:
                pass
        
        page.on("response", on_response)
        print("Navigating...")
        await page.goto("https://tijucas.atende.net/transparencia/item/despesas-publicas")
        await page.wait_for_timeout(15000)
        
        with open("all_requests.json", "w", encoding="utf-8") as f:
            json.dump(requests, f, indent=2, ensure_ascii=False)
            
        print(f"Logged {len(requests)} non-static responses.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
