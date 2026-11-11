"""
Drive the boot menu in a pseudo-terminal, simulating remote-control key presses.

Run with: python3 deploy/boot/tests/test_rewind_boot.py
"""

import os
import pty
import re
import select
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "rewind-boot"


def run(keys, default=None, delay="2"):
    conf = tempfile.mkdtemp()
    if default:
        (Path(conf) / "rewind").mkdir()
        (Path(conf) / "rewind" / "boot-default").write_text(default)
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.update(
            XDG_CONFIG_HOME=conf, REWIND_BOOT_DRY_RUN="1", REWIND_BOOT_DELAY=delay,
            TERM="linux", COLUMNS="80", LINES="24",
        )
        os.execv("/bin/bash", ["bash", str(SCRIPT)])
    out, start = b"", time.time()
    for key, wait in keys:
        time.sleep(wait)
        os.write(fd, key)
    while time.time() - start < 6:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            out += data
    os.waitpid(pid, 0)
    found = re.findall(rb"LAUNCH v\d", out)
    return found[-1].decode() if found else "NONE"


CASES = [
    ("timeout boots v1", [], None, "LAUNCH v1"),
    ("key 2 boots v2", [(b"2", 0.5)], None, "LAUNCH v2"),
    ("AZERTY e-acute boots v2", [("é".encode(), 0.5)], None, "LAUNCH v2"),
    ("down + OK boots v2", [(b"\x1b[B", 0.5), (b"\r", 0.3)], None, "LAUNCH v2"),
    ("default v2 on timeout", [], "v2", "LAUNCH v2"),
    ("default v2, up + OK boots v1", [(b"\x1b[A", 0.5), (b"\n", 0.3)], "v2", "LAUNCH v1"),
]

if __name__ == "__main__":
    failed = 0
    for name, keys, default, expected in CASES:
        got = run(keys, default)
        ok = got == expected
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {got}")
    sys.exit(1 if failed else 0)
