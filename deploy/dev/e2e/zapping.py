"""Zapping must play the requested playlist at once (YouTube keeps the old one otherwise).

Runs against the sandbox (deploy/dev/setup-sandbox). Needs playwright + system chromium."""
import asyncio
from playwright.async_api import async_playwright
KEYS = {2: "é", 3: '"', 4: "'", 6: "-"}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--autoplay-policy=no-user-gesture-required"])
        page = await b.new_page(viewport={"width": 720, "height": 576})
        await page.goto("http://127.0.0.1:8081/")
        await page.wait_for_timeout(2000)
        for n in (2, 3, 4, 2, 6, 3):
            await page.evaluate("k => window.dispatchEvent(new KeyboardEvent('keydown', {key: k}))", KEYS[n])
            for wait in (1500, 4000):
                await page.wait_for_timeout(wait)
                r = await page.evaluate("""() => ({want: rewind.current?.playlist_id, got: rewind.youtube.playlistId,
                    title: rewind.youtube.player?.getVideoData?.().title, inList: (rewind.youtube.player?.getPlaylist?.()||[]).includes(rewind.youtube.player?.getVideoData?.().video_id)})""")
                print(f"ch{n} +{wait}ms want={r['want'][-6:]} got={(r['got'] or '-')[-6:]} {'OK' if r['want']==r['got'] and r['inList'] else 'MISMATCH'} {(r['title'] or '')[:40]}")
        await b.close()
asyncio.run(main())
