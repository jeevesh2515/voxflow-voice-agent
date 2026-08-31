import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/cinematic_hero_audit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("=== 1. STAGE A: APERTURE (0px) ===")
        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUTPUT_DIR}/01_stage_a_aperture.png")
        print("  ✓ Saved 01_stage_a_aperture.png")

        print("=== 2. STAGE B: CAMERA ORBIT & BLUEPRINT (400px) ===")
        await page.evaluate("window.scrollTo({top: 400, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/02_stage_b_blueprint_orbit.png")
        print("  ✓ Saved 02_stage_b_blueprint_orbit.png")

        print("=== 3. STAGE B2: CONCENTRIC WAVE RINGS & HUD (800px) ===")
        await page.evaluate("window.scrollTo({top: 800, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/03_stage_b2_wave_rings.png")
        print("  ✓ Saved 03_stage_b2_wave_rings.png")

        print("=== 4. STAGE C: CONSOLE GLIDE-IN & ROUTING (1300px) ===")
        await page.evaluate("window.scrollTo({top: 1300, behavior: 'instant'})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/04_stage_c_console_glide_in.png")
        print("  ✓ Saved 04_stage_c_console_glide_in.png")

        print("=== 5. VOICE X-RAY SECTION (2400px) ===")
        xray = await page.query_selector("#voice-xray")
        if xray:
            await xray.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/05_voice_xray.png")
            print("  ✓ Saved 05_voice_xray.png")

        print("=== 6. DISPATCH SWITCHBOARD SECTION (3400px) ===")
        switchboard = await page.query_selector("#switchboard")
        if switchboard:
            await switchboard.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{OUTPUT_DIR}/06_switchboard.png")
            print("  ✓ Saved 06_switchboard.png")

        print("=== 7. FULL PAGE SNAPSHOT ===")
        await page.screenshot(path=f"{OUTPUT_DIR}/07_full_page.png", full_page=True)
        print("  ✓ Saved 07_full_page.png")

        await browser.close()
        print(f"\n🎉 Verification complete! Total console errors: {len(console_errors)}")

if __name__ == "__main__":
    asyncio.run(main())
