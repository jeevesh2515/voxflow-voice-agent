import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/final_perfection_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("1. Opening Landing Page (Testing Preloader & Initial Still Black Hole)...")
        await page.goto("http://127.0.0.1:3000/", wait_until="domcontentloaded")
        # Capture preloader if present
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{OUTPUT_DIR}/01_preloader_pulse.png")
        print("  ✓ Captured 01_preloader_pulse.png")

        # Wait for preloader dissolve (1.5s)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUTPUT_DIR}/02_still_blackhole_aperture.png")
        print("  ✓ Captured 02_still_blackhole_aperture.png")

        print("2. Verifying Zero Mouse Wobble on Black Hole...")
        await page.mouse.move(100, 100)
        await page.wait_for_timeout(200)
        await page.mouse.move(1300, 800)
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{OUTPUT_DIR}/03_blackhole_mouse_move_still.png")
        print("  ✓ Captured 03_blackhole_mouse_move_still.png")

        print("3. Scrolling into Stage C (Clean Headline & Docked Live Console)...")
        await page.evaluate("window.scrollTo(0, 950)")
        await page.wait_for_timeout(700)
        await page.screenshot(path=f"{OUTPUT_DIR}/04_stage_c_clean_hero.png")
        print("  ✓ Captured 04_stage_c_clean_hero.png")

        print("4. Testing Voice Persona Pills...")
        en_btn = page.get_by_text("Play English", exact=True)
        if await en_btn.count() > 0:
            await en_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/05_voice_en_active.png")
            print("  ✓ Captured 05_voice_en_active.png")

        print("5. Scrolling through StickyCapabilityShowcase (40/60 Notched Split)...")
        showcase = page.locator("#showcase, #capabilities, [data-showcase-root], section:has-text('DISPATCH')")
        if await showcase.count() > 0:
            await showcase.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/06_showcase_dispatch_radar.png")
            print("  ✓ Captured 06_showcase_dispatch_radar.png")

            # Scroll further into showcase for Step 2
            await page.evaluate("window.scrollBy(0, 700)")
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/07_showcase_warehouse_grid.png")
            print("  ✓ Captured 07_showcase_warehouse_grid.png")

            # Scroll further into showcase for Step 3
            await page.evaluate("window.scrollBy(0, 700)")
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/08_showcase_customer_stream.png")
            print("  ✓ Captured 08_showcase_customer_stream.png")

        print("6. Testing Parallax Quotes Section (Deep Starry Background)...")
        quotes = page.locator("[data-parallax-quotes], section:has-text('replaced 14 manual'), section:has-text('payback in 14 days')")
        if await quotes.count() > 0:
            await quotes.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/09_parallax_quotes_clean.png")
            print("  ✓ Captured 09_parallax_quotes_clean.png")

        print("7. Testing Multi-Depot UK Switchboard (Manchester Express)...")
        sb = page.locator("#switchboard")
        if await sb.count() > 0:
            await sb.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            man_hub = page.get_by_text("Manchester Express")
            if await man_hub.count() > 0:
                await man_hub.click()
                await page.wait_for_timeout(400)
            await page.screenshot(path=f"{OUTPUT_DIR}/10_switchboard_active.png")
            print("  ✓ Captured 10_switchboard_active.png")

        print("8. Testing 4-Hop Architecture Pipeline...")
        pipe = page.locator("#pipeline-section")
        if await pipe.count() > 0:
            await pipe.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            badge_text = await page.locator("#pipe-latency").inner_text()
            print(f"  Pipeline active readout: {badge_text}")
            await page.screenshot(path=f"{OUTPUT_DIR}/11_pipeline_active.png")
            print("  ✓ Captured 11_pipeline_active.png")

        print("9. Testing Interactive ROI Calculator...")
        roi = page.locator("#roi-section")
        if await roi.count() > 0:
            await roi.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/12_roi_calculator.png")
            print("  ✓ Captured 12_roi_calculator.png")

        print("10. Testing Bi-Directional Scroll Reversal Back to Top (0px)...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await page.wait_for_timeout(800)
        final_y = await page.evaluate("window.scrollY")
        print(f"  Final scroll Y: {final_y}px")
        await page.screenshot(path=f"{OUTPUT_DIR}/13_returned_stage_a_top.png")
        print("  ✓ Captured 13_returned_stage_a_top.png")

        await browser.close()
        print(f"\n🎉 Full Final Perfection Audit Complete! Browser console errors: {len(console_errors)}")
        if console_errors:
            print("Console Errors:", console_errors)

if __name__ == "__main__":
    asyncio.run(main())
