"""Verify all web pages and components using Playwright by logging in via Demo button."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("/Users/jeeveshsingale/.gemini/antigravity-ide/brain/77151200-5d27-4c24-bd34-d62a0efeb883/ui_audit")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_PAGES = [
    ("landing", "http://127.0.0.1:3000/"),
    ("pricing", "http://127.0.0.1:3000/pricing"),
    ("terms", "http://127.0.0.1:3000/terms"),
    ("privacy", "http://127.0.0.1:3000/privacy"),
    ("refund", "http://127.0.0.1:3000/refund"),
    ("signup", "http://127.0.0.1:3000/sign-up?plan=growth"),
    ("signin", "http://127.0.0.1:3000/sign-in"),
]

DASHBOARD_PAGES = [
    ("dashboard", "http://127.0.0.1:3000/dashboard"),
    ("orders", "http://127.0.0.1:3000/dashboard/orders"),
    ("calls", "http://127.0.0.1:3000/dashboard/calls"),
    ("stock", "http://127.0.0.1:3000/dashboard/stock"),
    ("settings", "http://127.0.0.1:3000/dashboard/settings"),
    ("simulator", "http://127.0.0.1:3000/dashboard/simulator"),
]

async def main():
    print("Launching Chromium...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5,
        )
        page = await context.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        
        # 1. Capture Public Pages
        for name, url in PUBLIC_PAGES:
            print(f"Navigating to {name} ({url})...", flush=True)
            try:
                await page.goto(url, wait_until="networkidle", timeout=10000)
                await asyncio.sleep(0.5)
                ss_path = SCREENSHOTS_DIR / f"{name}.png"
                await page.screenshot(path=str(ss_path), full_page=True)
                print(f"  ✓ Saved {name}.png ({ss_path.stat().st_size // 1024} KB)", flush=True)
            except Exception as e:
                print(f"  ⚠ Failed {name}: {e}", flush=True)

        # 2. Sign In via Demo Workspace Button
        print("\nSigning in via Demo Workspace button...", flush=True)
        await page.goto("http://127.0.0.1:3000/sign-in", wait_until="networkidle")
        demo_btn = page.locator("text=Open Read-Only Demo Workspace")
        if await demo_btn.count() > 0:
            await demo_btn.click()
            await page.wait_for_url("**/dashboard**", timeout=10000)
            await asyncio.sleep(1)
            print("  ✓ Successfully signed into Demo Dashboard!", flush=True)

        # 3. Capture Dashboard Pages
        for name, url in DASHBOARD_PAGES:
            print(f"Navigating to {name} ({url})...", flush=True)
            try:
                await page.goto(url, wait_until="networkidle", timeout=10000)
                await asyncio.sleep(1)
                ss_path = SCREENSHOTS_DIR / f"{name}.png"
                await page.screenshot(path=str(ss_path), full_page=True)
                print(f"  ✓ Saved {name}.png ({ss_path.stat().st_size // 1024} KB)", flush=True)
            except Exception as e:
                print(f"  ⚠ Failed {name}: {e}", flush=True)

        await browser.close()
        print(f"\n🎉 Audit complete! Captured screenshots in {SCREENSHOTS_DIR}", flush=True)
        print(f"Console errors: {len(console_errors)}", flush=True)
        if console_errors:
            for err in console_errors[:10]:
                print(f"  - {err}")

if __name__ == "__main__":
    asyncio.run(main())
