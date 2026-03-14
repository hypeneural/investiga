import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Navigate to Atende.net portal
        print("Navigating to portal...")
        await page.goto("https://tijucas.atende.net/transparencia/item/despesas-publicas")
        await page.wait_for_timeout(5000)
        
        # Take a screenshot to see what it looks like
        await page.screenshot(path="portal_debug.png")
        html = await page.content()
        with open("portal.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Saved portal.html and portal_debug.png. Page title:", await page.title())
        await browser.close()

asyncio.run(run())
