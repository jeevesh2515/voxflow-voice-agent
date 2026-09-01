import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/terminal_patterns_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("1. Opening Landing Page at 0px...")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUTPUT_DIR}/01_hero_blackhole_0px.png")
        print("  ✓ Captured 01_hero_blackhole_0px.png")

        print("2. Testing Mouse Hover on Black Hole...")
        await page.mouse.move(300, 300)
        await page.wait_for_timeout(300)
        await page.mouse.move(1100, 600)
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUTPUT_DIR}/02_hero_blackhole_hover.png")
        print("  ✓ Captured 02_hero_blackhole_hover.png")

        print("3. Scrolling to Stage B/C (Kinetic Text + Docked Console)...")
        await page.evaluate("window.scrollTo(0, 900)")
        await page.wait_for_timeout(700)
        await page.screenshot(path=f"{OUTPUT_DIR}/03_stage_c_docked_console.png")
        print("  ✓ Captured 03_stage_c_docked_console.png")

        print("4. Testing Voice Persona Pill buttons...")
        en_btn = page.get_by_text("Play English", exact=True)
        if await en_btn.count() > 0:
            await en_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/04_voice_persona_active.png")
            print("  ✓ Captured 04_voice_persona_active.png")

        print("5. Testing Asymmetric Capability Slider...")
        slider = page.locator("#capabilities, [data-slider-root], section:has-text('Capability')")
        if await slider.count() > 0:
            await slider.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/05_slider_initial.png")
            print("  ✓ Captured 05_slider_initial.png")

            # Test Next Button Click
            next_btn = page.locator("button[aria-label='Next capability'], button:has-text('›'), button:has-text('>')").first
            if await next_btn.count() > 0:
                await next_btn.click()
                await page.wait_for_timeout(500)
                await page.screenshot(path=f"{OUTPUT_DIR}/06_slider_next_card.png")
                print("  ✓ Captured 06_slider_next_card.png")

        print("6. Testing Parallax Quotes Section with Notched Borders...")
        quotes = page.locator("section:has-text('replaced'), section:has-text('payback'), [data-parallax-quotes]")
        if await quotes.count() > 0:
            await quotes.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/07_parallax_quotes.png")
            print("  ✓ Captured 07_parallax_quotes.png")

        print("7. Testing Multi-Depot Switchboard Hub Selection...")
        sb = page.locator("#switchboard")
        if await sb.count() > 0:
            await sb.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            man_hub = page.get_by_text("Manchester Express")
            if await man_hub.count() > 0:
                await man_hub.click()
                await page.wait_for_timeout(400)
            await page.screenshot(path=f"{OUTPUT_DIR}/08_switchboard_manchester.png")
            print("  ✓ Captured 08_switchboard_manchester.png")

        print("8. Testing 4-Hop Pipeline Architecture...")
        pipe = page.locator("#pipeline-section")
        if await pipe.count() > 0:
            await pipe.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/09_pipeline_section.png")
            print("  ✓ Captured 09_pipeline_section.png")

        print("9. Testing 2-Way Google Sheets Mirror...")
        sheets = page.locator("#sheets-section")
        if await sheets.count() > 0:
            await sheets.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/10_sheets_mirror.png")
            print("  ✓ Captured 10_sheets_mirror.png")

        print("10. Testing Interactive ROI Calculator...")
        roi = page.locator("#roi-section")
        if await roi.count() > 0:
            await roi.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/11_roi_calculator.png")
            print("  ✓ Captured 11_roi_calculator.png")

        print("11. Testing Pricing Section...")
        pricing = page.locator("#pricing-section")
        if await pricing.count() > 0:
            await pricing.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/12_pricing_section.png")
            print("  ✓ Captured 12_pricing_section.png")

        print("12. Testing Reverse Scroll Back to Top (0px)...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await page.wait_for_timeout(800)
        final_y = await page.evaluate("window.scrollY")
        print(f"  Final scroll Y: {final_y}px")
        await page.screenshot(path=f"{OUTPUT_DIR}/13_returned_top_0px.png")
        print("  ✓ Captured 13_returned_top_0px.png")

        await browser.close()
        print(f"\n✨ Terminal Patterns Audit Complete! Browser console errors: {len(console_errors)}")
        if console_errors:
            print("Errors:", console_errors)

if __name__ == "__main__":
    asyncio.run(main())
