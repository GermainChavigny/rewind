# v1 behaviors to carry over

Checklist of the subtle details v1 got right. Each item must be ported (or
consciously replaced) by v2. Tick items as they land.

## Hardware & system

- [ ] **A/V sync offset.** Video goes HDMI → SCART converter, audio goes out the
      analog jack (`analog-output-headphones`), not HDMI. The converter delays
      the picture, so v1 delays the audio by **+200 ms** with
      `pactl set-port-latency-offset … 200000`. Applied system-wide, so YouTube and
      movies are both fixed. v2: configurable offset in the admin, with a
      calibration screen (flash + beep), applied via PipeWire/PulseAudio.
- [ ] Forced output mode (v1: `HDMI-2` at 720×576) → configurable; auto-detected
      by default.
- [ ] No screen blanking / DPMS.
- [ ] System volume forced to 100%; the remote's volume keys change the
      *player* volume (±5%) and show the retro VOLUME OSD.
- [ ] Native cursor hidden; a pixel-art retro cursor (arrow/hand, sized in `vw`)
      is drawn instead, hidden when idle and when the mouse leaves the window.
- [ ] Ad blocking on YouTube via **uBlock Origin Lite** (MV3) loaded in the kiosk
      browser. The installer must fetch it.
- [ ] Chromium kiosk flags: autoplay without a user gesture,
      `AudioVideoTracks` (needed to switch audio tracks), no crash bubble, no
      update checks, tiny disk cache. (`--disable-web-security` is no longer
      needed once everything is same-origin.)
- [ ] Jackett: the launcher waits for `JackettUpdater` (segfault after an
      auto-update), systemd restarts it, and the API "kicks" it before a search
      if its port is closed.
- [ ] Remote (HAOBO air mouse): see the full mapping in "Remote control" below.
      v2: configurable keymap with a "learn key" mode.

## Remote control (v1 mapping, Linux)

Two **different** power buttons — do not mix them up:

| Button | What it does | Handled by |
|---|---|---|
| Remote **power** button (`KEY_POWER`) | Shuts down the **mini PC** | systemd-logind (`HandlePowerKey=poweroff`, Debian default) — the app never sees it |
| Remote **mute** button (`AudioVolumeMute`) | Turns the **TV** off/on through the Wi-Fi smart plug (Shelly) | the app (`/tv-power` proxy) |

| Key (`event.key`) | Action |
|---|---|
| `& é " ' ( - è _ ç` (digits 1–9 on AZERTY) | Channel 1–9. The channel logo bar shows for 3 s at boot and 2 s after each switch. The Movies channel shows the bar first, then opens the library after 900 ms (cancelled if you zap again). Any other channel closes the movie overlays and plays its playlist. |
| `à` (0) | Toggles the alarm. Voice feedback: "Réveil activé" / "Pas de réveil". |
| ↑ / ↓ | Alarm time ±10 min. **Also enables the alarm** and speaks the new time (volume 0.8). In the movie UI, scrolls the hovered list instead. |
| ← / → | Seek ±15 s (YouTube and movies). |
| Play/Pause | Play/pause. Resuming also requests full screen. |
| Next / Previous | YouTube: next/previous video in the playlist. Movies: next/previous item of the sorted library queue. Context-dependent. |
| Volume + / − | **Player** volume ±5 points (linear), retro VOLUME OSD. The system volume stays at 100%. v2: use a perceptual (log) curve so steps sound even. |
| PageUp / PageDown | Black veil over the **whole** UI (opacity 0–1). PageUp = darker, PageDown = lighter. **Non-linear steps**: 5% normally, 2% above 50% darkness, 1% above 80%, for fine control when very dark. Not persisted (resets on reload). v2: persist it. |
| Mute | TV power via the smart plug. TV on → pause playback (YouTube **or movie**) and turn the TV off; TV off → turn it on. (v1 bug: in movie mode it only paused the movie and left the TV on — v2 must also turn the TV off.) |
| Any key except Mute | Turns the TV on (smart plug). |
| Any key | Stops a ringing alarm. |
| Air mouse | Cursor-driven movie screens (big targets). |

v2 new requirement: the alarm needs a **visual** access too. Show an alarm OSD
(time + on/off) when adjusting it, a permanent discreet indicator when it is
armed, and a settings screen reachable from the TV and from the phone admin.
In v1 the only feedback is the voice.

Note: the alarm only fires while the PC is on and the kiosk is running; it then
turns the TV on through the plug and plays the alarm channel.

## YouTube channels

- [ ] Progress saved per playlist *and* per video, every 2.5 s.
- [ ] Never overwrite saved progress with an empty state (client and server
      guards).
- [ ] Per-channel flags: `noSave` (e.g. News always starts fresh), `isAlarm`
      (the alarm channel).
- [ ] Preferred quality `hd720`.
- [x] YouTube quirk: loading a playlist while another plays can keep playing a
      video of the OLD playlist (one-channel lag). v1 worked around it with
      `stopVideo()` + a delay before `loadPlaylist()`; v2 does the same and also
      forces the requested playlist if a foreign video starts.
- [ ] A local intro video loops at boot until a channel or movie takes over.
- [ ] A channel selector overlay with logos (v2: choose a logo or icon, plus an
      optional text name).

## Movies & series playback

- [ ] Transcode plan from cheapest to most expensive: `remux` (H.264 + AAC/MP3)
      → `audio` (copy the video, re-encode the audio) → `full` (H.264 baseline
      3.0, 720 wide, AAC). Keep **all** audio tracks; `+faststart`; write to a
      temp file, then rename.
- [ ] Embedded fr/en text subtitles extracted to WebVTT. OpenSubtitles lookup
      by **moviehash** first, then IMDb/TMDB/title. Automatic resync with
      **ffsubsync**.
- [ ] Live subtitle offset HUD (top right, ±0.1 s, shown on mouse move, auto-hide)
      while the movie keeps playing. The offset is **per language** and persisted.
      It is re-applied when a VTT loads late, without shifting twice, and tracks
      use `hidden` mode so cues can be shifted before being shown.
- [ ] Pause screen: fit mode `contain` (16:9 letterbox) ⇄ `cover` (4:3 crop),
      subtitles language, audio track, clickable progress bar, back to the
      library.
- [ ] A transparent "mouse catch" layer above `<video>` (mouse events on video
      are unreliable over the letterbox bars).
- [ ] Watched at ≥ 92%. Resume position. Library order: active downloads →
      recently played → recently added.
- [ ] Series: "Next SxxExx" HUD (on mouse move once the episode counts as watched;
      always shown when paused); episode list popup; resume the last episode.
- [ ] Downloads: 3 in parallel, **1 transcode at a time** (weak CPU). Priority to
      the lowest season/episode. Season packs, with a single-episode fallback.
      Jobs resume after a reboot. Airing shows are rechecked every 12 h.
- [ ] Torrent reachability probe (…/✓/✗) before downloading.
- [ ] Movie Advisor: a provider chain (Gemini → OpenRouter → fallbacks) where the
      first that answers wins. Excludes "Forget"-ed titles and owned titles.
      French title shown; English title used for the torrent search.

## Alarm

- [ ] Progressive alarm: the sound goes 0 → 1 over 30 s; YouTube fades in after
      20 s, over 15 s; it stops after 5 min max or on any key.
- [ ] The time is announced by voice (speechSynthesis "Google français", with
      recorded number clips as a fallback). Spoken confirmations: "Réveil
      activé" / "Pas de réveil".

## Look & feel

- [ ] Staggered fade-in of screen elements, with a soft WebAudio "tick" per
      element and a "beep" on clicks (synthesized; the AudioContext is woken on
      the first click).
- [ ] Retro header with clock, date and a weather icon (next hour). Clicking it
      opens the 90s weather channel popup (Morning / Afternoon / Evening + min/max).
- [ ] SVG weather icons (emoji render as "tofu" in the mono font).
- [ ] The VOLUME OSD is made only of characters (green `|`, dark `-`), with no
      background.
- [ ] Shared CRT footer shortcuts `[MOVIES] [SEARCH] [ADVISOR]`.
- [ ] Delete needs a confirmation (two clicks).
- [ ] Advisor: a quote from a fictional 90s TV critic (Michael Harper) on each
      opening.
- [ ] Type sizes tuned for a small CRT at 720×576.

## Robustness

- [ ] Atomic, fsynced writes (SQLite in v2).
- [ ] Never kill unrelated processes at startup (v1 ran `killall python3`).
- [ ] Rotated logs (v1's `api.log` grew to 26 MB).
