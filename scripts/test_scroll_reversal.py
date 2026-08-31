import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        page = await context.new_page()

        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("Testing scroll down...")
        for y in [500, 1200, 2000, 3500, 5000]:
            await page.evaluate(f"window.scrollTo({{top: {y}, behavior: 'smooth'}})")
            await page.wait_for_timeout(400)
            cur_y = await page.evaluate("window.scrollY")
            print(f"  Target: {y}px -> Current: {cur_y}px")

        print("\nTesting scroll back up...")
        for y in [3500, 2000, 800, 0]:
            await page.evaluate(f"window.scrollTo({{top: {y}, behavior: 'smooth'}})")
            await page.wait_for_timeout(400)
            cur_y = await page.evaluate("window.scrollY")
            print(f"  Target: {y}px -> Current: {cur_y}px")

        await browser.close()
        print("\nTest finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
