# Linger tools

Scripts for regenerating the demo video, the iOS Shortcut and the app icons.
Requires macOS, Python 3 and `ffmpeg`.

## Setup (once)

```sh
cd tools
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium
```

## Demo video → `../linger-demo.mp4`

```sh
./make_demo_video.sh
```

This script:
1. Starts `linger_play.py` on port 5056.
2. Records the UI with Playwright (`record_demo.py`): intro, choose the sample clip, 75%, play, the 130% preset, play.
3. Fetches the processed audio from `/process`.
4. Measures when playback really starts (`measure_sync.py`).
5. Muxes the audio in with ffmpeg and stops the server.

Intermediate files go to `tools/build/`, which is safe to delete. Notes:
- If the app is already running on 5056, use `PORT=5057 ./make_demo_video.sh`. Use `OUT=<path>` to write the video somewhere else.
- Captions and the fake cursor are injected only into the recording browser. Edit the `__caption(...)` lines in `record_demo.py` to change them.
- `measure_sync.py` reads the audio player's progress bar at fixed pixel coordinates (`BAR_Y`, `BAR_X`). If the card layout changes, update them. The script exits with a message if it can't find the bar.

## iOS Shortcut → `../Linger.shortcut`

```sh
python3 make_shortcut.py "http://<mac-ip>:5056/process"
shortcuts sign --mode anyone --input Linger-unsigned.shortcut --output ../Linger.shortcut
```

The URL is only the default; the Shortcut asks for it on import. Find the Mac's IP with `ipconfig getifaddr en0`.

## App icons → `../static/`

```sh
./venv/bin/python make_icons.py
```

## Assets

- `assets/podcast-clip.m4a`: 8.5s spoken sample used in the demo, made with macOS `say -v Samantha`.
- `assets/old_icons/`: the original dark/amber icons, from before the restyle.
