# Session log — 2026-10-05

Work done with Claude Code on the audio tempo app, originally "Audio Slower", now **Linger**.

## Starting point

- `slowdown.py`: Flask app (port 5055). Upload MP3/M4A/WAV, pick 70–130% speed, ffmpeg `atempo` changes tempo with pitch preserved, result is **downloaded**.
- `slowdown_play.py`: newer variant (port 5056). Same, but the result **plays in the page** and it's installable as a PWA (manifest + icons in `static/`).
- Dark theme (near-black background, amber accent, Bebas Neue / JetBrains Mono). Not a git repo.

## What changed, in order

1. **Demo video.** I recorded a demo of the play version with Playwright (headless Chromium): choose file → drag slider to 75% → Process & Play → 130% preset → play. A fake cursor and step captions were injected into the recording browser only. Headless video has no audio, so the processed audio was fetched from the real `/process` endpoint and muxed in with ffmpeg, synced to playback start.
2. **Restyle: white and blue gradient.** The reference (magnific.com UI kit) returned 403, so the design follows the usual gradient-UI-kit conventions:
   - White background with faint cyan/violet corner glows.
   - White card, 24px radius, soft blue shadow.
   - Gradient `#36c6ff → #3b6cff → #6a4dff` used for the title, speed readout, slider fill and pill button.
   - Fonts: Poppins for headings, DM Sans for labels.
   - The 🎵 emoji became a gradient badge with an SVG note.
   - Icons were redrawn: same waveform bars, white on the gradient.
   - Theme colors are set through CSS variables in `:root` (`--accent`, `--grad`, `--grad-h`, …).
3. **Intro screen.** A pure-CSS splash: the waveform logo (bars gently pulse) and the wordmark. It fades out at about 2.0–2.45s, then the card fades in and slides up starting at 2.45s (made sequential to avoid an overlap). Respects `prefers-reduced-motion`.
4. **Renamed to Linger.**
   - Changed: page title, intro wordmark, card heading, `apple-mobile-web-app-title`, manifest `name` / `short_name`.
   - Kept: the "Slower / Faster" speed label, since it describes the speed rather than naming the app.
   - Fixed: gradient text (`background-clip: text`) clipped the descender of the "g". Added `padding-bottom: 0.12em; margin-bottom: -0.12em` to the wordmarks.
5. **Files renamed.** `slowdown.py` → `linger.py`, `slowdown_play.py` → `linger_play.py`. Nothing referenced the old names. The old `audio-slower-demo.mp4` was deleted and replaced by `linger-demo.mp4`.
6. **iOS share sheet.** Web Share Target isn't supported by iOS Safari (to my knowledge), so a PWA can't appear in the iOS share sheet. Instead I built **`Linger.shortcut`**, an Apple Shortcut signed with `shortcuts sign --mode anyone`:
   - Appears in the share sheet for media and files.
   - Asks for the server URL on import (default `http://192.168.0.177:5056/process`).
   - Lets you pick a speed from a list.
   - POSTs a multipart form (`file`, `speed`) to `/process`.
   - Opens the result in Quick Look.
   - Manual build steps are below.
   - **Fix (same day):** the first version gave "No file uploaded". A capture server plus a debug shortcut run with `shortcuts run` showed that the `file` form field, encoded as a bare `WFTextTokenAttachment`, is silently dropped, and only `speed` is sent. File fields need a `WFTokenAttachmentParameterState` wrapper. With it, a proper multipart upload arrives (filename and `audio/x-m4a`). `tools/make_shortcut.py` is fixed and `Linger.shortcut` rebuilt. **Confirmed working on iPhone** (sharing from Files and Messages).
7. **Debug mode off.** `app.run(debug=False, ...)` in both apps, because the server is now reachable on the LAN. The Werkzeug debugger must not be exposed there. Verified the server reports "Debug mode: off" and processes requests on the LAN address.

## Current project contents

| File | Purpose |
|---|---|
| `linger_play.py` | Main app: process and play in the browser, PWA. `python3 linger_play.py` → http://localhost:5056 |
| `linger.py` | Variant that downloads the processed file. Port 5055 |
| `static/` | PWA icons (blue gradient waveform), 180/192/512 px |
| `linger-demo.mp4` | 38s demo video, 1440×900, H.264/AAC, includes intro screen and synced audio |
| `Linger.shortcut` | Signed iOS/macOS Shortcut for share-sheet processing |
| `tools/` | Scripts to rebuild the demo video, Shortcut and icons (see `tools/README.md`) |
| `.backup/` | Original `slowdown.py` / `slowdown_play.py` (dark amber theme, pre-intro, debug on) |
| `SESSION_LOG.md` | This file |

Requirements: Python 3 with Flask, and `ffmpeg` on PATH.

## Using the Shortcut

1. On the Mac: `python3 linger_play.py`. Allow incoming connections if macOS asks.
2. AirDrop `Linger.shortcut` to the iPhone → **Add Shortcut** → confirm the server URL. The phone must be on the same Wi-Fi as the Mac. If the Mac's IP changes, edit the Text action at the top of the shortcut.
3. Share an audio file (Voice Memos, Files, …) → **Linger** → pick speed → plays in Quick Look.

Manual build, if the import fails:
1. **Show in Share Sheet** on, input types Media and Files.
2. **Text**: `http://<mac-ip>:5056/process`
3. **List**: `70, 75, 80, 85, 90, 95, 105, 110, 120, 130`
4. **Choose from List**.
5. **Get Contents of URL**:
   - URL: the Text from step 2
   - Method: POST
   - Request Body: Form
   - Fields: File `file` = Shortcut Input; Text `speed` = Chosen Item
6. **Quick Look** with the Contents of URL.

Limits: MP3/M4A/WAV only, and DRM-protected Apple Music tracks can't be shared. Server errors show up as JSON text in Quick Look.

## Notes and open items

- **Helper scripts are in `tools/`** (see `tools/README.md`):
  - `make_demo_video.sh`: rebuilds the demo video end to end
  - `record_demo.py`, `measure_sync.py`: the recording and sync steps it runs
  - `make_shortcut.py`: builds the Shortcut
  - `make_icons.py`: regenerates the icons
  - `assets/`: the sample clip and the original amber icons

  The one-off restyle and intro patch scripts weren't kept, since their changes are already in the code.
- **Audio sync in the video** was measured from the audio player's progress bar in the recorded frames. Playback starts about 0.5s after the "Playing at…" status appears, because of decode time. The sync is accurate to roughly ±0.1s.
- **Flask's built-in server** is fine for personal LAN use. Use `waitress` or `gunicorn` if it's ever exposed more widely.
- **Possible next steps:**
  - Android share target (`share_target` in the manifest plus a receiving route).
  - A native iOS app with a Share Extension, which could process on-device with `AVAudioUnitTimePitch`, no server needed.
  - Renaming the project folder from `Slowdown`.
