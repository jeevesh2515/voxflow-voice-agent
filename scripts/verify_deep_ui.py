import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/deep_ui_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("=== PART 1: HERO & AUDIO SYNTHESIS ===")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Capture initial Hero
        hero_el = await page.query_selector("section")
        if hero_el:
            await hero_el.screenshot(path=f"{OUTPUT_DIR}/01_hero_idle.png")
            print("  ✓ Saved 01_hero_idle.png")

        # Click English Audio Preview button
        print("  Clicking English audio preview button...")
        await page.click("text=Play English Sample")
        await page.wait_for_timeout(800)
        if hero_el:
            await hero_el.screenshot(path=f"{OUTPUT_DIR}/02_hero_playing_en.png")
            print("  ✓ Saved 02_hero_playing_en.png (active waveform state)")
        await page.wait_for_timeout(2600)

        # Click Hindi Audio Preview button
        print("  Clicking Hindi audio preview button...")
        await page.click("text=Play Hindi Sample")
        await page.wait_for_timeout(800)
        if hero_el:
            await hero_el.screenshot(path=f"{OUTPUT_DIR}/03_hero_playing_hi.png")
            print("  ✓ Saved 03_hero_playing_hi.png (active waveform state)")
        await page.wait_for_timeout(2600)

        print("\n=== PART 2: TRUST METRICS STRIP ===")
        metrics_el = await page.query_selector("section:nth-of-type(2)")
        if metrics_el:
            await metrics_el.screenshot(path=f"{OUTPUT_DIR}/04_metrics_strip.png")
            print("  ✓ Saved 04_metrics_strip.png")

        print("\n=== PART 3: DUAL-POV TELEMETRY ===")
        dual_pov = await page.query_selector("section:has-text('Caller hears a human')")
        if dual_pov:
            await dual_pov.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await dual_pov.screenshot(path=f"{OUTPUT_DIR}/05_dual_pov.png")
            print("  ✓ Saved 05_dual_pov.png")

        print("\n=== PART 4: 4-HOP PIPELINE ===")
        pipeline = await page.query_selector("section:has-text('Four hops')")
        if pipeline:
            await pipeline.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await pipeline.screenshot(path=f"{OUTPUT_DIR}/06_four_hop_pipeline.png")
            print("  ✓ Saved 06_four_hop_pipeline.png")

        print("\n=== PART 5: SHEETS LIVE MIRROR ===")
        sheets = await page.query_selector("section:has-text('Google Sheet')")
        if sheets:
            await sheets.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await sheets.screenshot(path=f"{OUTPUT_DIR}/07_sheets_mirror.png")
            print("  ✓ Saved 07_sheets_mirror.png")

        print("\n=== PART 6: BENTO GRID & FAQ ===")
        bento = await page.query_selector("section:has-text('Built for UK operations')")
        if bento:
            await bento.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await bento.screenshot(path=f"{OUTPUT_DIR}/08_bento_grid.png")
            print("  ✓ Saved 08_bento_grid.png")

        faq = await page.query_selector("section:has-text('FAQ')")
        if faq:
            await faq.scroll_into_view_if_needed()
            details = await page.query_selector("details")
            if details:
                await details.click()
                await page.wait_for_timeout(300)
            await faq.screenshot(path=f"{OUTPUT_DIR}/09_faq_expanded.png")
            print("  ✓ Saved 09_faq_expanded.png")

        # Full Landing Page Capture
        await page.screenshot(path=f"{OUTPUT_DIR}/10_full_landing.png", full_page=True)
        print("\n  ✓ Saved 10_full_landing.png (Complete Landing Page)")

        await browser.close()
        print("\n🎉 Deep visual audit complete!")

if __name__ == "__main__":
    asyncio.run(main())
