"""Walk through the movie screens and take screenshots (no download, no AI call).

Runs against the sandbox (deploy/dev/setup-sandbox). Needs playwright + system chromium.
Usage: python movies.py [out_dir] [width height]
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (720, 576)


async def key(page, k):
    await page.evaluate("k => window.dispatchEvent(new KeyboardEvent('keydown', {key: k}))", k)


async def shot(page, name):
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(OUT / f"{name}.png"))
    print("shot", name)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        page = await b.new_page(viewport={"width": W, "height": H})
        page.on("pageerror", lambda e: print("PAGE ERROR:", e))
        page.on("console", lambda m: m.type == "error" and print("console:", m.text))
        await page.goto("http://127.0.0.1:8081/")
        await page.wait_for_timeout(2500)

        # Library channel (9) → grid first, then the library opens.
        await key(page, "ç")
        await page.wait_for_timeout(1800)
        print("screen:", await page.evaluate("rewind.screen"))
        await shot(page, "01-library")
        await page.get_by_role("button", name="Séries").first.click()
        await shot(page, "02-library-series")
        await page.locator(".detail .crt-btn", has_text="Épisodes").click()
        await page.wait_for_timeout(2500)
        await shot(page, "03-series")

        # Search: keyboard, typed on the real keyboard, then results.
        await page.evaluate("rewind.goSearch()")
        await page.wait_for_timeout(400)
        for ch in "groundhog day":
            await page.keyboard.press("Space" if ch == " " else ch)
        await shot(page, "04-keyboard")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(5000)
        await shot(page, "05-results")
        await page.wait_for_timeout(12000)
        await page.locator(".list .row").nth(2).click()
        await shot(page, "06-results-probed")

        # Advisor (criteria + picker), no recommendation request.
        await page.evaluate("rewind.goAdvisor()")
        await page.wait_for_timeout(800)
        await shot(page, "07-advisor")
        await page.locator(".grid .crit").nth(6).click()
        await shot(page, "08-advisor-picker")
        await page.locator(".opt").nth(3).click()

        # Play the first ready movie, then pause it.
        await page.evaluate("rewind.goLibrary()")
        await page.wait_for_timeout(800)
        play = page.locator(".detail .crt-btn.primary")
        print("play button:", await play.inner_text())
        await play.click()
        await page.wait_for_timeout(4000)
        state = await page.evaluate(
            "(() => { const v = document.querySelector('video.movie');"
            " return {t: v.currentTime, paused: v.paused, w: v.videoWidth, err: v.error && v.error.code,"
            " tracks: [...v.textTracks].map(t => t.language + ':' + t.mode)} })()"
        )
        print("movie:", state)
        await page.mouse.move(W / 2, H / 2)
        await page.mouse.move(W / 2 + 20, H / 2 + 10)
        await shot(page, "09-playing")
        await key(page, "MediaPlayPause")
        await page.wait_for_timeout(800)
        await shot(page, "10-paused")
        await key(page, "MediaPlayPause")
        await page.wait_for_timeout(800)
        print("resumed:", not await page.evaluate("document.querySelector('video.movie').paused"))
        await key(page, "&")  # zap to channel 1: the movie stops
        await page.wait_for_timeout(1500)
        print("movie stopped:", await page.evaluate("document.querySelector('video.movie').classList.contains('hidden')"))
        await b.close()


asyncio.run(main())
