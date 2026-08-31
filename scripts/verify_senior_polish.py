import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/senior_polish_audit"
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
        await page.screenshot(path=f"{OUTPUT_DIR}/01_hero_desktop.png")
        print("  ✓ Saved 01_hero_desktop.png")

        print("2. Testing English voice button...")
        en_btn = page.get_by_text("Play English", exact=True)
        if await en_btn.count() > 0:
            await en_btn.click()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/02_en_voice_active.png")
            print("  ✓ Saved 02_en_voice_active.png")

        print("3. Testing Hindi voice button...")
        hi_btn = page.get_by_text("Play Hindi", exact=True)
        if await hi_btn.count() > 0:
            await hi_btn.click()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/03_hi_voice_active.png")
            print("  ✓ Saved 03_hi_voice_active.png")

        print("4. Inspecting Voice X-Ray section...")
        xray = page.locator("#voice-xray")
        if await xray.count() > 0:
            await xray.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/04_voice_xray.png")
            print("  ✓ Saved 04_voice_xray.png")

        print("5. Inspecting Multi-Depot Switchboard...")
        sb = page.locator("#switchboard")
        if await sb.count() > 0:
            await sb.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            # Click Manchester Express hub
            man_hub = page.get_by_text("Manchester Express")
            if await man_hub.count() > 0:
                await man_hub.click()
                await page.wait_for_timeout(400)
            await page.screenshot(path=f"{OUTPUT_DIR}/05_switchboard_manchester.png")
            print("  ✓ Saved 05_switchboard_manchester.png")

        print("6. Testing ROI Calculator interaction...")
        roi = page.locator("#roi-section")
        if await roi.count() > 0:
            await roi.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/06_roi_calculator.png")
            print("  ✓ Saved 06_roi_calculator.png")

        print("7. Testing Pricing Matrix...")
        pricing = page.locator("#pricing-section")
        if await pricing.count() > 0:
            await pricing.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/07_pricing_matrix.png")
            print("  ✓ Saved 07_pricing_matrix.png")

        print("8. Testing smooth scroll return to top (0px)...")
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await page.wait_for_timeout(800)
        final_y = await page.evaluate("window.scrollY")
        print(f"  Final scroll Y: {final_y}px")
        await page.screenshot(path=f"{OUTPUT_DIR}/08_scroll_returned_top.png")
        print("  ✓ Saved 08_scroll_returned_top.png")

        await browser.close()
        print(f"\n🎉 Senior Polish QA Complete! Console errors: {len(console_errors)}")

if __name__ == "__main__":
    asyncio.run(main())
