import asyncio
from playwright.async_api import async_playwright
import os

os.makedirs("/tmp/voxflow_live_audit", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("https://voxflow-voice-agent.vercel.app", wait_until="networkidle")
        await asyncio.sleep(2.5)

        # 1. Opening Centered Black Hole (Y=0)
        await page.screenshot(path="/tmp/voxflow_live_audit/01_aperture.png")
        print("Captured 01_aperture.png")

        # 2. Stage 2: Punchline 1 (Y=700)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(700, { immediate: true }) : window.scrollTo(0, 700)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_live_audit/02_punchline_1.png")
        print("Captured 02_punchline_1.png")

        # 3. Stage 3: Punchline 2 (Y=1450)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(1450, { immediate: true }) : window.scrollTo(0, 1450)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_live_audit/03_punchline_2.png")
        print("Captured 03_punchline_2.png")

        # 4. Stage 4: Docked Headline & Live Console (Y=2400)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(2400, { immediate: true }) : window.scrollTo(0, 2400)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_live_audit/04_docked_hero.png")
        print("Captured 04_docked_hero.png")

        # 5. Overhauled Quotes Section
        await page.evaluate("const el = document.querySelector('.parallax-quotes'); if (el && window.__lenis) { window.__lenis.scrollTo(el, { immediate: true }); } else if (el) { el.scrollIntoView(); }")
        await asyncio.sleep(1.5)
        await page.screenshot(path="/tmp/voxflow_live_audit/05_quotes_section.png")
        print("Captured 05_quotes_section.png")

        await browser.close()

asyncio.run(main())
