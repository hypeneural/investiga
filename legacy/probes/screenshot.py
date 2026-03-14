import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Loading https://tijucas.atende.net/transparencia/ ...")
        await page.goto("https://tijucas.atende.net/transparencia/")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="tijucas_transparencia.png", full_page=True)
        html = await page.content()
        with open("tijucas_transparencia.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved tijucas_transparencia.png and tijucas_transparencia.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
