# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repository base, v1 data import (the v1/v2 boot menu was removed once v1 was retired) | ✅ |
| 1 | Backend: configuration, SQLite, module system, admin API | ✅ |
| 2 | TV interface (Svelte) faithful to v1: channels, player, alarm, weather, HUD | ✅ |
| 3 | Movies, series, downloads, Movie Advisor | 🔍 to validate on the TV |
| 4 | Phone admin: first-run wizard, settings, channel logos, remote key learning | 🔍 to validate on the TV and the phone |
| 5 | `install.sh`, cage + Chromium kiosk, updates | 🔍 to validate on the TV |
| 6 | Extras: voice commands, HDMI-CEC, disk image | |

## Feedback backlog

From the first install by a friend (2026-11-14). Done 2026-11-17, to validate.

- [x] Install: install missing dependencies automatically (Python?).
      `install.sh` checked Python 3.11 before installing any package; it now
      installs python3 (and wget when there is no curl/wget) first, and checks
      the version once the packages are in.
- [x] Admin changes not live: the movie/series buttons in search and the
      Advisor button only show up after a page refresh. The TV reloaded its
      modules but not the library features.
- [x] Series: show the size of each episode (ready episodes, detail panel).
- [x] The Groq key seemed to have disappeared and had to be entered again.
      Likely cause: masked keys in lists were restored by position, so removing
      or adding a provider above Groq gave it another slot's key (or none).
      They are now matched by name / kind / address.
- [x] "Movie ready" announcement: off by default, can be turned on in the
      admin (Vidéothèque).
- [x] Subtitles: the download failed for "Tenet". Every OpenSubtitles download
      failed: the API answers 301 to unsorted query parameters and httpx does
      not follow redirects (v1's requests did). Movies with embedded subtitles
      hid it.
- [x] Advisor: more recent release periods (2010s, 2020s, "Récents" = the last
      two years).
- [x] Alarm: delay when the chime starts ("La sonnerie démarre après").
- [x] Remote: hold the brightness or volume key to repeat it (phone remote;
      the USB remote relies on the keyboard auto-repeat).
- [x] Virtual remote: refresh the channel buttons when the channels change
      in the admin.
