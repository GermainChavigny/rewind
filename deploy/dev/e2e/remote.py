"""Phone remote ↔ TV: modes, touchpad, phone keyboard, home key, settings QR, shutdown card.

Runs against an instance with a FAKE shutdown (`[system] shutdown = "fake"`),
e.g. the sandbox: REWIND_URL=http://127.0.0.1:8081 (default). Never point it
at the real TV instance: it presses the computer's power key.
Needs playwright + system chromium:  uv run --with playwright python remote.py
"""

import asyncio
import json
import os
import urllib.request

from playwright.async_api import async_playwright

BASE = os.environ.get("REWIND_URL", "http://127.0.0.1:8081")
OUT = os.environ.get("SHOTS", ".")


def check(label, ok):
    print(("OK   " if ok else "FAIL ") + label)
    return ok


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            executable_path="/usr/bin/chromium", args=["--autoplay-policy=no-user-gesture-required"]
        )
        tv = await b.new_page(viewport={"width": 720, "height": 576})
        await tv.goto(BASE + "/")
        # Boot: the channel grid never flashes over the intro video.
        flashed = False
        for _ in range(20):
            flashed |= await tv.evaluate(
                "!!document.querySelector('.grid-wrap.shown')"
            )
            await tv.wait_for_timeout(150)
        check("boot: no channel grid over the intro", not flashed)
        first_run = await tv.evaluate("rewind.firstRun")
        if first_run:
            check("first run: QR code shown at once", await tv.evaluate("rewind.overlay") == "setup")
        else:
            await tv.evaluate("rewind.runAction('seek_forward')")
            check("→ on the welcome screen opens the QR code", await tv.evaluate("rewind.overlay") == "setup")
        await tv.wait_for_timeout(600)
        check("QR code drawn", await tv.locator(".qr svg path").count() == 1)
        await tv.screenshot(path=f"{OUT}/tv-setup.png")
        await tv.evaluate("rewind.runAction('seek_backward')")
        check("← closes it", await tv.evaluate("rewind.overlay") is None)
        check("settings corner on the welcome screen", await tv.locator(".corner").count() == 1)

        phone = await b.new_page(viewport={"width": 390, "height": 760}, has_touch=True)
        await phone.goto(BASE + "/remote/")
        await phone.wait_for_timeout(1200)
        check("tv mode: no touchpad", await phone.locator(".pad").count() == 0)
        check(
            "tv mode: computer power key",
            await phone.locator(".key.machine").count() == 1,
        )
        await phone.screenshot(path=f"{OUT}/remote-tv.png")

        # Movies: the remote switches layout.
        await tv.evaluate("rewind.goLibrary()")
        await phone.wait_for_timeout(800)
        check("movies mode: touchpad shown", await phone.locator(".pad").count() == 1)
        check("movies mode: no channel keys", await phone.locator(".key.number").count() == 0)
        check("movies mode: home key", await phone.locator(".key.home").count() == 1)
        await phone.screenshot(path=f"{OUT}/remote-movies.png")

        # Touchpad: drag moves the TV cursor (the retro cursor follows).
        def cursor_pos():
            return tv.evaluate(
                "getComputedStyle(document.querySelector('.cursor')).transform"
            )

        before = await cursor_pos()
        box = await phone.locator(".pad").bounding_box()
        x, y = box["x"] + 40, box["y"] + 40
        cdp = await phone.context.new_cdp_session(phone)

        async def touch(kind, px, py):
            points = [] if kind == "touchEnd" else [{"x": px, "y": py}]
            await cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})

        await touch("touchStart", x, y)
        for i in range(1, 15):
            await touch("touchMove", x + i * 8, y + i * 5)
            await phone.wait_for_timeout(16)
        await touch("touchEnd", 0, 0)
        await tv.wait_for_timeout(500)
        check("pad drag moves the TV cursor", await cursor_pos() != before)

        # Phone keyboard types into the TV search.
        await tv.evaluate("rewind.goSearch()")
        await phone.wait_for_timeout(700)
        field = phone.locator(".typing input")
        check("TV keyboard open: phone text field shown", await field.count() == 1)
        await field.fill("alien")
        await field.dispatch_event("input")
        await phone.wait_for_timeout(600)
        check("typed text reaches the TV", await tv.evaluate("rewind.kbText") == "alien")
        await tv.screenshot(path=f"{OUT}/tv-keyboard.png")

        # Home: back to the welcome screen; the remote resets.
        await phone.locator(".key.home").dispatch_event("pointerup")
        await tv.wait_for_timeout(600)
        state = await tv.evaluate("({i: rewind.intro, s: rewind.screen, o: rewind.overlay, g: rewind.gridVisible})")
        check("home: intro, no screen, no grid", state == {"i": True, "s": None, "o": None, "g": False})
        await phone.wait_for_timeout(400)
        check("home: remote back to the tv layout", await phone.locator(".pad").count() == 0)

        # Computer power: confirmation, then the end-of-broadcast card.
        await phone.locator(".key.machine").dispatch_event("pointerup")
        check("power key asks first", await phone.locator(".dialog").count() == 1)
        await phone.screenshot(path=f"{OUT}/remote-confirm.png")
        await phone.locator(".d-btn.danger").click()
        await tv.wait_for_timeout(800)
        check("TV shows the end of broadcast", await tv.evaluate("rewind.shuttingDown"))
        await tv.screenshot(path=f"{OUT}/tv-shutdown.png")
        await b.close()

    layout = json.load(urllib.request.urlopen(BASE + "/api/remote/layout"))
    print("layouts saved:", {k: v is not None for k, v in layout["layouts"].items()})


asyncio.run(main())
