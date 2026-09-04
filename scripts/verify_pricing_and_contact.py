import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Verify Pricing Page
        print("Visiting http://localhost:3000/pricing...")
        await page.goto("http://localhost:3000/pricing", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/pricing_page_hero_elevated.png")

        # Scroll down to volume estimator
        await page.evaluate("window.scrollBy(0, 700)")
        await page.wait_for_timeout(600)
        await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/pricing_page_calculator_matrix.png")

        # 2. Verify Contact Page
        print("Visiting http://localhost:3000/contact...")
        await page.goto("http://localhost:3000/contact", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/contact_page_loaded.png")

        # Test copying email
        copy_btn = page.locator("button[aria-label='Copy founder email to clipboard']")
        if await copy_btn.count() > 0:
            await copy_btn.click()
            await page.wait_for_timeout(300)
            await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/contact_email_copied.png")

        # Fill and submit form
        await page.fill("#name-input", "Jane Doe")
        await page.fill("#email-input", "jane@acmefreight.co.uk")
        await page.fill("#company-input", "Acme Freight UK")
        await page.fill("#message-input", "We handle 2,000 inbound depot verification calls monthly. Can we connect our UK DID number?")
        await page.wait_for_timeout(400)
        await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/contact_form_filled.png")

        # Submit form
        await page.click("button[type='submit']")
        await page.wait_for_timeout(1200)
        await page.screenshot(path="/Users/jeeveshsingale/.gemini/antigravity-ide/brain/febe5097-3fe3-4107-82c2-bc8b1c9724a3/contact_form_submitted_success.png")

        await browser.close()
        print("Verification captures completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
