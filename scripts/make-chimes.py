"""Synthesises the soft alarm chimes (stdlib only, then ffmpeg → mp3).

Usage: python scripts/make-chimes.py
Writes frontend/public/audio/chimes/{bells,musicbox,dawn,drops}.mp3. Each is a
calm ~8 s phrase ending in silence, meant to loop while its volume fades in.
"classic.mp3" (the v1 chime) is converted from the v1 wav separately.
"""

import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

RATE = 32000
OUT = Path(__file__).resolve().parent.parent / "frontend/public/audio/chimes"




def hz(name: str) -> float:
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    semis = names[name[0]] + (1 if "#" in name else 0) + 12 * (int(name[-1]) - 4)
    return 440.0 * 2 ** (semis / 12)


def render(length_s: float, events: list[tuple[float, callable]]) -> list[float]:
    buf = [0.0] * int(length_s * RATE)
    for start, voice in events:
        i0 = int(start * RATE)
        for i, v in enumerate(voice()):
            if i0 + i >= len(buf):
                break
            buf[i0 + i] += v
    return buf


def bell(freq: float, dur: float = 4.5, amp: float = 0.32):
    # Soft bell: a few slightly inharmonic partials, gentle attack, long decay.
    partials = [(1.0, 1.0), (2.0, 0.35), (2.76, 0.18), (5.4, 0.05)]

    def gen():
        n = int(dur * RATE)
        for i in range(n):
            t = i / RATE
            env = min(1.0, t / 0.012) * math.exp(-t * 1.3)
            yield amp * env * sum(
                a * math.sin(2 * math.pi * freq * m * t) * math.exp(-t * m * 0.5) for m, a in partials
            )

    return gen


def pluck(freq: float, dur: float = 1.6, amp: float = 0.28):
    # Music-box tine: bright attack, quick decay, a little octave shimmer.
    def gen():
        for i in range(int(dur * RATE)):
            t = i / RATE
            env = min(1.0, t / 0.004) * math.exp(-t * 3.2)
            yield amp * env * (
                math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * freq * 2 * t)
            )

    return gen


def marimba(freq: float, dur: float = 1.4, amp: float = 0.34):
    def gen():
        for i in range(int(dur * RATE)):
            t = i / RATE
            env = min(1.0, t / 0.006) * math.exp(-t * 4.5)
            yield amp * env * (
                math.sin(2 * math.pi * freq * t) + 0.12 * math.sin(2 * math.pi * freq * 4 * t)
            )

    return gen


def pad(freqs: list[float], dur: float = 7.0, amp: float = 0.16):
    # Warm swelling chord with a slow tremolo.
    def gen():
        for i in range(int(dur * RATE)):
            t = i / RATE
            env = math.sin(math.pi * min(1.0, t / dur)) ** 2
            trem = 0.85 + 0.15 * math.sin(2 * math.pi * 0.7 * t)
            yield amp * env * trem * sum(
                math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2 * t + 0.4)
                for f in freqs
            )

    return gen


CHIMES = {
    "bells": (9.0, [(0.0, bell(hz("C5"))), (0.7, bell(hz("E5"))), (1.4, bell(hz("G5"))),
                    (3.2, bell(hz("C5"), amp=0.22))]),
    "musicbox": (8.0, [(i * 0.38, pluck(hz(n))) for i, n in enumerate(
        ["E5", "G5", "C6", "B5", "G5", "A5", "E5", "G5", "D5", "C5"])]),
    "dawn": (8.0, [(0.0, pad([hz("A3"), hz("C#4"), hz("E4")])),
                   (1.5, bell(hz("E5"), amp=0.12)), (3.0, bell(hz("A5"), amp=0.1))]),
    "drops": (8.0, [(t, marimba(hz(n))) for t, n in [
        (0.0, "G4"), (0.45, "D5"), (0.9, "B4"), (1.6, "A4"), (2.05, "E5"), (2.5, "D5"),
        (3.4, "G4"), (3.85, "B4")]]),
}  # fmt: skip


def write(name: str, samples: list[float]) -> None:
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = 0.7 / peak
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / f"{name}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"".join(struct.pack("<h", int(s * scale * 32767)) for s in samples))
        out = OUT / f"{name}.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "96k", str(out)],
            check=True,
        )
        print(out, out.stat().st_size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (length, events) in CHIMES.items():
        write(name, render(length, events))
