import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/manus_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("=== 1. LOADING HOME ROUTE ===")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Capture initial Hero at top (0px)
        await page.screenshot(path=f"{OUTPUT_DIR}/01_hero_initial.png")
        print("  ✓ Saved 01_hero_initial.png")

        # 2. Test Audio Persona Trigger (EN)
        print("  Clicking English persona button...")
        btn_en = await page.query_selector("button:has-text('English')")
        if btn_en:
            await btn_en.click()
            await page.wait_for_timeout(800)
            await page.screenshot(path=f"{OUTPUT_DIR}/02_hero_playing_en.png")
            print("  ✓ Saved 02_hero_playing_en.png")
            await page.wait_for_timeout(1500)

        # 3. Test Audio Persona Trigger (Hindi)
        print("  Clicking Hindi persona button...")
        btn_hi = await page.query_selector("button:has-text('Hindi')")
        if btn_hi:
            await btn_hi.click()
            await page.wait_for_timeout(800)
            await page.screenshot(path=f"{OUTPUT_DIR}/03_hero_playing_hi.png")
            print("  ✓ Saved 03_hero_playing_hi.png")
            await page.wait_for_timeout(1500)

        # 4. Scroll Step 1: Pinned Hero Transition (500px)
        print("  Scrolling to 600px (Pinned hero & signal labels)...")
        await page.evaluate("window.scrollTo({top: 600, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/04_scroll_600px_pinned_stage.png")
        print("  ✓ Saved 04_scroll_600px_pinned_stage.png")

        # 5. Scroll Step 2: Narrative Section & Kinetic Word Illumination (1300px)
        print("  Scrolling to 1400px (Narrative & word scrub)...")
        await page.evaluate("window.scrollTo({top: 1400, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/05_scroll_1400px_narrative.png")
        print("  ✓ Saved 05_scroll_1400px_narrative.png")

        # 6. Scroll Step 3: Dual-POV Telemetry (2200px)
        print("  Scrolling to 2400px (Dual-POV Telemetry)...")
        await page.evaluate("window.scrollTo({top: 2400, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/06_scroll_2400px_dual_pov.png")
        print("  ✓ Saved 06_scroll_2400px_dual_pov.png")

        # 7. Scroll Step 4: 4-Hop Pipeline HUD (3400px)
        print("  Scrolling to 3500px (4-Hop Pipeline)...")
        await page.evaluate("window.scrollTo({top: 3500, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/07_scroll_3500px_pipeline.png")
        print("  ✓ Saved 07_scroll_3500px_pipeline.png")

        # 8. Scroll Step 5: ROI Calculator (4500px)
        print("  Scrolling to 4600px (ROI Calculator)...")
        await page.evaluate("window.scrollTo({top: 4600, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/08_scroll_4600px_roi.png")
        print("  ✓ Saved 08_scroll_4600px_roi.png")

        # 9. Scroll Step 6: Pricing Matrix (5600px)
        print("  Scrolling to 5700px (Pricing Matrix)...")
        await page.evaluate("window.scrollTo({top: 5700, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/09_scroll_5700px_pricing.png")
        print("  ✓ Saved 09_scroll_5700px_pricing.png")

        # 10. Complete Page Screenshot
        print("  Capturing full page snapshot...")
        await page.screenshot(path=f"{OUTPUT_DIR}/10_full_page.png", full_page=True)
        print("  ✓ Saved 10_full_page.png")

        await browser.close()
        print(f"\n🎉 Verification complete! Total console errors: {len(console_errors)}")
        if console_errors:
            print("Errors encountered:", console_errors)

if __name__ == "__main__":
    asyncio.run(main())
