import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/scroll_effects_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("1. Loading home route...")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("2. Testing 4-Hop Pipeline scroll activation...")
        pipe = page.locator("#pipeline-section")
        await pipe.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        # Check latency badge value and active cards
        badge_text = await page.locator("#pipe-latency").inner_text()
        print(f"  Pipeline latency readout: {badge_text}")
        await page.screenshot(path=f"{OUTPUT_DIR}/01_pipeline_active.png")
        print("  ✓ Saved 01_pipeline_active.png")

        print("3. Testing Dual-POV Telemetry stream...")
        tele = page.locator("#solutions")
        await tele.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{OUTPUT_DIR}/02_telemetry_stream.png")
        print("  ✓ Saved 02_telemetry_stream.png")

        print("4. Testing Sheets Mirror live commit flash...")
        sheets = page.locator("#sheets-section")
        await sheets.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        commit_label = await page.locator("#sheet-commit-label").inner_text()
        print(f"  Sheets commit label: {commit_label}")
        await page.screenshot(path=f"{OUTPUT_DIR}/03_sheets_mirror.png")
        print("  ✓ Saved 03_sheets_mirror.png")

        print("5. Testing scroll back to top...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/04_hero_back_at_top.png")
        print("  ✓ Saved 04_hero_back_at_top.png")

        await browser.close()
        print(f"\n🎉 Scroll Effects Verification Complete! Console errors: {len(console_errors)}")

if __name__ == "__main__":
    asyncio.run(main())
