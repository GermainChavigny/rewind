"""Hidden layers never catch clicks; the channel grid shows while paused.

Runs against the sandbox (deploy/dev/setup-sandbox). Needs playwright + system chromium."""
import asyncio
from playwright.async_api import async_playwright
async def key(page, k):
    await page.evaluate("k => window.dispatchEvent(new KeyboardEvent('keydown', {key: k}))", k)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--autoplay-policy=no-user-gesture-required"])
        page = await b.new_page(viewport={"width": 720, "height": 576})
        await page.goto("http://127.0.0.1:8081/")
        await page.wait_for_timeout(1500)
        await key(page, "é"); await page.wait_for_timeout(8000)   # channel 2, grid hidden again
        # (c) hidden grid must not catch clicks: click where tile 6 would be
        await page.mouse.click(470, 250); await page.wait_for_timeout(500)
        print("hidden grid click kept channel 2:", await page.evaluate("rewind.current.number") == 2)
        # (b) pause → grid shown
        await key(page, "MediaPlayPause"); await page.wait_for_timeout(1500)
        print("paused:", await page.evaluate("rewind.paused"),
              "grid shown:", await page.evaluate("document.querySelector('.grid-wrap').classList.contains('shown')"))
        await page.wait_for_timeout(400); await page.screenshot(path="paused.png")
        await key(page, "MediaPlayPause"); await page.wait_for_timeout(1500)
        print("resumed, grid hidden:", not await page.evaluate("document.querySelector('.grid-wrap').classList.contains('shown')"))
        # (a) alarm screen: nothing from the grid under it
        await page.evaluate("rewind.openScreen('alarm')"); await page.wait_for_timeout(600)
        hits = await page.evaluate("""() => [[150,150],[360,250],[560,400],[360,520]].map(([x,y]) => {
            const el = document.elementFromPoint(x, y); return el.closest('.screen') ? 'screen' : (el.closest('.grid-wrap') ? 'GRID' : el.tagName) })""")
        print("alarm screen hit-test:", hits)
        await b.close()
asyncio.run(main())
