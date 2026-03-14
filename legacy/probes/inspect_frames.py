import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating...")
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
        
        print(f"Current URL: {page.url}")
        print(f"Number of frames: {len(page.frames)}")
        
        for i, frame in enumerate(page.frames):
            print(f"\n--- Frame {i} URL: {frame.url} ---")
            try:
                # Try to get all visible text in the frame
                text = await frame.inner_text("body")
                print("TEXT START:")
                print(text[:500]) # Print first 500 chars
            except Exception as e:
                print(f"Could not read frame text: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
