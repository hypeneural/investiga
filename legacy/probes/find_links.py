import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to https://tijucas.atende.net/transparencia/")
        await page.goto("https://tijucas.atende.net/transparencia/")
        await page.wait_for_timeout(5000)
        
        print("Looking for Despesas links...")
        locators = await page.get_by_text("Despesas", exact=False).all()
        print(f"Found {len(locators)} elements containing 'Despesas'")
        
        for loc in locators:
            try:
                tag = await loc.evaluate("el => el.tagName")
                classes = await loc.evaluate("el => el.className")
                text = await loc.inner_text()
                href = await loc.get_attribute("href")
                print(f"TAG: {tag}, CLASSES: {classes}, TEXT: {text}, HREF: {href}")
            except Exception as e:
                print(f"Error evaluating element: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
