# Linger

Linger is a small web app that slows down or speeds up audio without changing its pitch. You upload an MP3, M4A, WAV or Opus file, choose a speed from 70% to 130%, and Linger gives you back the re-timed audio. It's useful for podcasts, voice memos, language practice or learning music by ear.

It runs on a Raspberry Pi on the home network (`10.0.0.202`) and can be used from any browser on the same network. It runs on a Mac too, for development. It can be installed as a home-screen app (PWA), and an Apple Shortcut lets you send audio to it from the iPhone share sheet.

▶️ **Demo:** [`linger-demo.mp4`](linger-demo.mp4) (38 s, with audio)

## Features

- **Pitch-preserving tempo change** using ffmpeg's `atempo` filter
- **Speed range 70–130%**, set with a slider or preset buttons
- **Plays in the browser.** The processed audio plays right away in the page.
- **Installable PWA** with a manifest and home-screen icons
- **iOS share sheet support** via a signed Apple Shortcut (`Linger.shortcut`)
- **Light theme:** white with a blue-violet gradient, plus an animated intro screen that respects `prefers-reduced-motion`

## Requirements

- Python 3 with [Flask](https://flask.palletsprojects.com/) and [Waitress](https://docs.pylonsproject.org/projects/waitress/) (`linger_play.py` runs on Waitress)
- [`ffmpeg`](https://ffmpeg.org/) on your `PATH`

```sh
sudo apt install ffmpeg python3-flask python3-waitress   # Raspberry Pi OS
pip install flask waitress && brew install ffmpeg        # macOS
```

## Usage

```sh
python3 linger_play.py
```

Open <http://10.0.0.202:5056> (or <http://localhost:5056> on the machine itself), choose a file, set the speed and press **Process & Play**.

Linger listens on `0.0.0.0`, so other devices on your Wi-Fi can reach it. To run it somewhere other than the Pi, find that machine's IP with `hostname -I` (Linux) or `ipconfig getifaddr en0` (macOS).

There's also a variant that **downloads** the processed file instead of playing it:

```sh
python3 linger.py      # http://localhost:5055
```

Output files are named `<name>-<speed>-<slower|faster><ext>`, for example `interview-75-slower.m4a`.

### API

Both apps expose the same endpoint:

```
POST /process
Content-Type: multipart/form-data
  file   audio file (.mp3, .m4a, .wav, .opus), max 200 MB
  speed  integer 70–130 (default 90)
```

It returns the processed audio. On error it returns JSON `{"error": ...}`.

```sh
curl -F file=@clip.m4a -F speed=80 http://10.0.0.202:5056/process -o clip-80.m4a
```

### iPhone share sheet

iOS Safari doesn't support Web Share Target, so Linger uses an Apple Shortcut instead.

1. Make sure `linger_play.py` is running on the Pi.
2. On the iPhone, open `http://10.0.0.202:5056` in Safari and tap **Get the share-sheet Shortcut** at the bottom of the page (or AirDrop `Linger.shortcut`). Tap **Add Shortcut** and confirm the server URL. The default is `http://10.0.0.202:5056/process`.
3. Share any audio file (from Voice Memos, Files, Messages and so on), choose **Linger**, then pick a speed. The result opens in Quick Look.

The phone has to be on the same Wi-Fi network as the Pi. If the server moves, rebuild the Shortcut with the new address (see [`tools/README.md`](tools/README.md)); signing it needs a Mac. DRM-protected Apple Music tracks can't be shared.

## Project structure

| Path | Purpose |
|---|---|
| `linger_play.py` | Main app: process and play in the browser, PWA (port 5056) |
| `linger.py` | Variant that downloads the result (port 5055) |
| `static/` | PWA icons (180/192/512 px) |
| `Linger.shortcut` | Signed iOS/macOS Shortcut for the share sheet |
| `ios/` | Native iPhone app for the App Store; processes audio on the device (see [`ios/README.md`](ios/README.md)) |
| `linger-demo.mp4` | Demo video |
| `tools/` | Scripts that rebuild the demo video, Shortcut and icons (see [`tools/README.md`](tools/README.md)) |
| `SESSION_LOG.md` | Detailed log of the development session |

## How it was built

Linger was built with [Claude Code](https://claude.com/claude-code), Anthropic's agentic coding CLI. Development went step by step, through conversation:

1. **Core app.** The project began as *Audio Slower*: a single-file Flask app that passes uploads through `ffmpeg -filter:a atempo=<speed>`. The HTML, CSS and JS are embedded in the Python file, so there's no build step. A second version played the result in the page and added a PWA manifest and icons.
2. **Demo video.** Claude Code wrote a Playwright script that drives the UI in headless Chromium, with an injected fake cursor and captions. Headless recordings have no sound, so the processed audio was fetched from the real `/process` endpoint. `measure_sync.py` found the moment playback starts by reading the audio player's progress bar in the recorded frames. ffmpeg then muxed in the audio, accurate to about ±0.1 s.
3. **Redesign.** The original dark/amber theme was replaced with a white and blue gradient look: Poppins and DM Sans fonts, a gradient badge and gradient controls. Colors are defined as CSS variables, and the icons were regenerated with Pillow (`tools/make_icons.py`).
4. **Intro screen and rename.** A pure-CSS splash animation was added and the app was renamed **Linger**. A small padding fix stopped gradient text from clipping the descender of the "g".
5. **iOS Shortcut.** `tools/make_shortcut.py` generates the Shortcut plist, and `shortcuts sign` signs it. The first version failed with "No file uploaded". Debugging with a capture server showed that the file form field needs a `WFTokenAttachmentParameterState` wrapper, or iOS silently drops it. After that fix the Shortcut was confirmed working on an iPhone.
6. **Hardening.** Flask debug mode was turned off because the server is reachable on the LAN.

See [`SESSION_LOG.md`](SESSION_LOG.md) for the full step-by-step account.

## Notes

- `linger_play.py` is served by Waitress, a production WSGI server. `linger.py` still uses Flask's built-in server, which is fine for personal use on a home network.
- A native iPhone app now lives in `ios/` and processes audio on the device with `AVAudioUnitTimePitch`.
- Ideas for later: an Android share target.
