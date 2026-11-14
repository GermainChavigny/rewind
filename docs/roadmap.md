# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repository base, v1/v2 boot menu, v1 data import | ✅ |
| 1 | Backend: configuration, SQLite, module system, admin API | ✅ |
| 2 | TV interface (Svelte) faithful to v1: channels, player, alarm, weather, HUD | ✅ |
| 3 | Movies, series, downloads, Movie Advisor | 🔍 to validate on the TV |
| 4 | Phone admin: first-run wizard, settings, channel logos, remote key learning | 🔍 to validate on the TV and the phone |
| 5 | `install.sh`, cage + Chromium kiosk, updates | 🔍 to validate on the TV |
| 6 | Extras: voice commands, HDMI-CEC, disk image | |

## Feedback backlog

From the first install by a friend (2026-11-14). Not started.

- [ ] Install: install missing dependencies automatically (Python?).
- [ ] Admin changes not live: the movie/series buttons in search and the
      Advisor button only show up after a page refresh.
- [ ] Series: show the size of each episode?
- [ ] The Groq key seemed to have disappeared and had to be entered again.
- [ ] "Movie ready" announcement: off by default, can be turned on in the admin.
- [ ] Subtitles: the download failed for "Tenet". Check whether it is that
      movie or subtitle downloads in general.
- [ ] Advisor: add more recent release periods.
- [ ] Alarm: allow delaying when the ringing starts.
- [ ] Remote: hold the brightness or volume key to repeat it, instead of
      tapping many times.
- [ ] Virtual remote: refresh the channel buttons when the channels change
      in the admin.
