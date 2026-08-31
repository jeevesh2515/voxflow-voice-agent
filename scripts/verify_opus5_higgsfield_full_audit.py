import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/opus5_higgsfield_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("=== STAGE A: Pure Aperture Frame (Scroll 0px) ===")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUTPUT_DIR}/01_stage_a_aperture_0px.png")
        print("  ✓ Captured 01_stage_a_aperture_0px.png")

        print("=== STAGE A: Mouse Hover / 3D Pointer Parallax ===")
        await page.mouse.move(200, 200)
        await page.wait_for_timeout(300)
        await page.mouse.move(1200, 700)
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUTPUT_DIR}/02_stage_a_mouse_parallax.png")
        print("  ✓ Captured 02_stage_a_mouse_parallax.png")

        print("=== STAGE B: Blueprint Morph & HUD Diagnostics (Scroll 450px) ===")
        await page.evaluate("window.scrollTo(0, 450)")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/03_stage_b_hud_and_wireframe.png")
        print("  ✓ Captured 03_stage_b_hud_and_wireframe.png")

        print("=== STAGE C: Core Docks Right, Headline & Console Glide In (Scroll 900px) ===")
        await page.evaluate("window.scrollTo(0, 900)")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/04_stage_c_docked_console.png")
        print("  ✓ Captured 04_stage_c_docked_console.png")

        print("=== INTERACTION 1: Voice Persona Playback (English & Hindi) ===")
        en_btn = page.get_by_text("Play English", exact=True)
        if await en_btn.count() > 0:
            await en_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/05_voice_en_active.png")
            print("  ✓ Captured 05_voice_en_active.png")

        hi_btn = page.get_by_text("Play Hindi", exact=True)
        if await hi_btn.count() > 0:
            await hi_btn.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/06_voice_hi_active.png")
            print("  ✓ Captured 06_voice_hi_active.png")

        print("=== INTERACTION 2: Voice X-Ray Spectrogram ===")
        xray = page.locator("#voice-xray")
        if await xray.count() > 0:
            await xray.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/07_voice_xray_section.png")
            print("  ✓ Captured 07_voice_xray_section.png")

        print("=== INTERACTION 3: Multi-Depot Switchboard (Manchester Hub) ===")
        sb = page.locator("#switchboard")
        if await sb.count() > 0:
            await sb.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            man_hub = page.get_by_text("Manchester Express")
            if await man_hub.count() > 0:
                await man_hub.click()
                await page.wait_for_timeout(400)
            await page.screenshot(path=f"{OUTPUT_DIR}/08_switchboard_active.png")
            print("  ✓ Captured 08_switchboard_active.png")

        print("=== INTERACTION 4: 4-Hop Pipeline Architecture ===")
        pipe = page.locator("#pipeline-section")
        if await pipe.count() > 0:
            await pipe.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            latency_badge = await page.locator("#pipe-latency").inner_text()
            print(f"  Pipeline active readout: {latency_badge}")
            await page.screenshot(path=f"{OUTPUT_DIR}/09_pipeline_section.png")
            print("  ✓ Captured 09_pipeline_section.png")

        print("=== INTERACTION 5: 2-Way Google Sheets Live Mirror ===")
        sheets = page.locator("#sheets-section")
        if await sheets.count() > 0:
            await sheets.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            commit_badge = await page.locator("#sheet-commit-label").inner_text()
            print(f"  Sheets commit badge: {commit_badge}")
            await page.screenshot(path=f"{OUTPUT_DIR}/10_sheets_mirror.png")
            print("  ✓ Captured 10_sheets_mirror.png")

        print("=== INTERACTION 6: ROI & Payback Engine ===")
        roi = page.locator("#roi-section")
        if await roi.count() > 0:
            await roi.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{OUTPUT_DIR}/11_roi_calculator.png")
            print("  ✓ Captured 11_roi_calculator.png")

        print("=== INTERACTION 7: Pricing Matrix Toggle ===")
        pricing = page.locator("#pricing-section")
        if await pricing.count() > 0:
            await pricing.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            annual_toggle = page.get_by_text("Annual (Save 20%)")
            if await annual_toggle.count() > 0:
                await annual_toggle.click()
                await page.wait_for_timeout(300)
            await page.screenshot(path=f"{OUTPUT_DIR}/12_pricing_annual.png")
            print("  ✓ Captured 12_pricing_annual.png")

        print("=== INTERACTION 8: Reversing Scroll Back to Top (0px) ===")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await page.wait_for_timeout(800)
        final_y = await page.evaluate("window.scrollY")
        print(f"  Scroll returned to Y = {final_y}px")
        await page.screenshot(path=f"{OUTPUT_DIR}/13_returned_stage_a.png")
        print("  ✓ Captured 13_returned_stage_a.png")

        await browser.close()
        print(f"\n✨ Full Audit Complete! Browser console errors: {len(console_errors)}")
        if console_errors:
            print("Errors:", console_errors)

if __name__ == "__main__":
    asyncio.run(main())
