"""Synthesizes the demo's sound effects into public/sfx/*.wav (numpy only).

Run from docs/demo: python3 scripts/make-sfx.py
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "public" / "sfx"
rng = np.random.default_rng(7)


def t(seconds: float) -> np.ndarray:
    return np.arange(int(SR * seconds)) / SR


def env(n: int, attack: float = 0.005, decay: float = 8.0) -> np.ndarray:
    x = np.arange(n) / SR
    a = np.clip(x / attack, 0, 1) if attack else 1
    return a * np.exp(-decay * x)


def lowpass(x: np.ndarray, k: float) -> np.ndarray:
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def save(name: str, x: np.ndarray, gain: float = 0.8) -> None:
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# The app's own click: a 1180 Hz square blip.
x = t(0.06)
save("click", np.sign(np.sin(2 * np.pi * 1180 * x)) * env(len(x), 0.001, 60), 0.5)

# Soft tick (screen elements popping in, volume steps).
x = t(0.04)
save("tick", np.sin(2 * np.pi * 720 * x) * env(len(x), 0.001, 90), 0.4)

# TV static (zapping).
x = t(0.35)
noise = rng.uniform(-1, 1, len(x))
save("static", (noise - lowpass(noise, 0.05)) * np.minimum(1, (0.35 - x) * 12), 0.55)

# CRT power-on: a low thump, then the 15 kHz-ish whine settling (kept audible).
x = t(1.0)
thump = np.sin(2 * np.pi * 55 * x) * env(len(x), 0.002, 9)
whine = np.sin(2 * np.pi * (7800 + 600 * np.exp(-4 * x)) * x) * 0.12 * env(len(x), 0.05, 2.5)
crackle = rng.uniform(-1, 1, len(x)) * env(len(x), 0.001, 25) * 0.6
save("poweron", thump + whine + crackle, 0.8)

# Remote "beam": a quick rising chirp, sci-fi style.
x = t(0.18)
f = 900 + 2600 * x / 0.18
save("beam", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.004, 14), 0.35)

# VHS rewind: motor whir rising in pitch, with tape hiss.
x = t(0.75)
f = 180 + 900 * (x / 0.75) ** 1.5
motor = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25
hiss = rng.uniform(-1, 1, len(x)) * 0.35
save("rewind", lowpass(motor + hiss, 0.25) * np.minimum(1, x * 20) * np.minimum(1, (0.75 - x) * 20), 0.6)

# Keyboard: a few different key clicks.
for i in range(4):
    x = t(0.05)
    click = rng.uniform(-1, 1, len(x)) * env(len(x), 0.0005, 160)
    body = np.sin(2 * np.pi * (1800 + 400 * i) * x) * env(len(x), 0.0005, 120) * 0.5
    save(f"key{i}", click + body, 0.35)

# Sparkle: a fast glittering arpeggio (star wipe).
x = t(0.7)
y = np.zeros(len(x))
for k, note in enumerate([2093, 2637, 3136, 4186, 3136, 4186, 5274]):
    start = int(k * 0.07 * SR)
    seg = x[: len(x) - start]
    y[start:] += np.sin(2 * np.pi * note * seg) * env(len(seg), 0.002, 10)
save("sparkle", y, 0.3)

# Whoosh: filtered noise swelling and fading (the other transitions).
x = t(0.45)
noise = rng.uniform(-1, 1, len(x))
swell = np.sin(np.pi * x / 0.45) ** 2
save("whoosh", lowpass(noise, 0.08) * swell, 0.45)

print("sfx written to", OUT)
