import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to https://tijucas.atende.net/transparencia/")
        await page.goto("https://tijucas.atende.net/transparencia/")
        await page.wait_for_timeout(5000)
        
        print("Clicking Despesas...")
        locators = await page.get_by_text("Despesas", exact=True).all()
        for loc in locators:
            tag = await loc.evaluate("el => el.tagName")
            if tag == "SPAN":
                await loc.click()
                print("Clicked Despesas span!")
                break
                
        await page.wait_for_timeout(5000)
        await page.screenshot(path="despesas_menu.png")
        
        html = await page.content()
        with open("despesas_menu.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Saved despesas_menu.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
