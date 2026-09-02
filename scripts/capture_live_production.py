import asyncio
from playwright.async_api import async_playwright
import os

os.makedirs("/tmp/voxflow_v2_audit", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("https://voxflow-voice-agent.vercel.app", wait_until="networkidle")
        await asyncio.sleep(2.5)

        # 1. Opening Centered Black Hole (Y=0)
        await page.screenshot(path="/tmp/voxflow_v2_audit/01_aperture_seamless.png")
        print("Captured 01_aperture_seamless.png")

        # 2. Stage 2: Punchline 1 Reveal (around Y=900 of 500vh stage)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(900, { immediate: true }) : window.scrollTo(0, 900)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_v2_audit/02_punchline_1_char_reveal.png")
        print("Captured 02_punchline_1_char_reveal.png")

        # 3. Stage 3: Punchline 2 Reveal (around Y=2100 of 500vh stage)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(2100, { immediate: true }) : window.scrollTo(0, 2100)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_v2_audit/03_punchline_2_char_reveal.png")
        print("Captured 03_punchline_2_char_reveal.png")

        # 4. Stage 4: Docked Headline & Live Console (around Y=3400)
        await page.evaluate("window.__lenis ? window.__lenis.scrollTo(3400, { immediate: true }) : window.scrollTo(0, 3400)")
        await asyncio.sleep(1.2)
        await page.screenshot(path="/tmp/voxflow_v2_audit/04_docked_hero.png")
        print("Captured 04_docked_hero.png")

        # 5. Overhauled Quotes Section
        await page.evaluate("const el = document.querySelector('.parallax-quotes'); if (el && window.__lenis) { window.__lenis.scrollTo(el, { immediate: true }); } else if (el) { el.scrollIntoView(); }")
        await asyncio.sleep(1.5)
        await page.screenshot(path="/tmp/voxflow_v2_audit/05_quotes_section.png")
        print("Captured 05_quotes_section.png")

        await browser.close()

asyncio.run(main())
