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

        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Scroll into #capabilities
        cap = page.locator("#capabilities")
        box = await cap.bounding_box()
        print(f"#capabilities top: {box['y']}px, height: {box['height']}px")

        # Step 1: Start of section
        await page.evaluate(f"window.scrollTo(0, {box['y'] + 100})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/showcase_step1_dispatch.png")
        print("  ✓ Captured showcase_step1_dispatch.png")

        # Step 2: 30% through
        await page.evaluate(f"window.scrollTo(0, {box['y'] + 600})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/showcase_step2_warehouse.png")
        print("  ✓ Captured showcase_step2_warehouse.png")

        # Step 3: 60% through
        await page.evaluate(f"window.scrollTo(0, {box['y'] + 1200})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/showcase_step3_support.png")
        print("  ✓ Captured showcase_step3_support.png")

        # Step 4: 90% through
        await page.evaluate(f"window.scrollTo(0, {box['y'] + 1800})")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUTPUT_DIR}/showcase_step4_erp.png")
        print("  ✓ Captured showcase_step4_erp.png")

        await browser.close()
        print("🎉 Step captures complete!")

if __name__ == "__main__":
    asyncio.run(main())
