import asyncio
from playwright.async_api import async_playwright
import os

os.makedirs("/tmp/voxflow_audit", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Standard desktop viewport
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        
        # Wait 2s for preloader dissolve
        await asyncio.sleep(2.0)
        
        # 1. Opening Centered Black Hole Aperture
        await page.screenshot(path="/tmp/voxflow_audit/01_centered_aperture.png")
        print("Captured 01_centered_aperture.png")
        
        # 2. Scroll into Punchline 1 (around 650px)
        await page.evaluate("window.scrollTo(0, 650)")
        await asyncio.sleep(0.8)
        await page.screenshot(path="/tmp/voxflow_audit/02_punchline_1.png")
        print("Captured 02_punchline_1.png")
        
        # 3. Scroll into Punchline 2 (around 1400px)
        await page.evaluate("window.scrollTo(0, 1400)")
        await asyncio.sleep(0.8)
        await page.screenshot(path="/tmp/voxflow_audit/03_punchline_2.png")
        print("Captured 03_punchline_2.png")
        
        # 4. Scroll into Docked Stage (around 2400px)
        await page.evaluate("window.scrollTo(0, 2400)")
        await asyncio.sleep(0.8)
        await page.screenshot(path="/tmp/voxflow_audit/04_docked_stage.png")
        print("Captured 04_docked_stage.png")
        
        # 5. Scroll to Quotes Section
        quotes_el = await page.query_selector(".parallax-quotes")
        if quotes_el:
            await quotes_el.scroll_into_view_if_needed()
            await asyncio.sleep(1.0)
            await page.screenshot(path="/tmp/voxflow_audit/05_quotes_section.png")
            print("Captured 05_quotes_section.png")
        
        await browser.close()

asyncio.run(main())
