"""Find when each clip actually starts playing in the recorded video.

Reads the <audio> player's progress bar in frames shortly after each playback mark in
events.json: start = frame_time - (fill fraction * clip duration). The bar only redraws
every ~250ms so it lags; we take the median of 5 samples minus 0.1s.

    python measure_sync.py video/<name>.webm   ->  prints and writes sync.json (seconds)

BAR_Y / BAR_X assume the 1440x900 recording and the current card layout. If the layout
changes, grab a frame during playback and update them to the progress bar's row/extent.
"""
import json
import subprocess
import sys

from PIL import Image

BAR_Y = 775
BAR_X = range(636, 845)

video = sys.argv[1]
events = json.load(open("events.json"))


def estimate(t, dur):
    out = f"sync_{t:.2f}.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", video,
                    "-frames:v", "1", out], check=True)
    im = Image.open(out).convert("RGB")
    sums = [sum(im.getpixel((x, BAR_Y))) for x in BAR_X]
    track = [x for x, v in zip(BAR_X, sums) if v < 300]   # played + unplayed track
    fill = [x for x, v in zip(BAR_X, sums) if v < 60]     # played portion (near black)
    if not track:
        sys.exit(f"no progress bar found at y={BAR_Y} in {out}; update BAR_Y/BAR_X")
    a, b = track[0], track[-1]
    f = fill[-1] if fill else a
    return t - (f - a) / (b - a) * dur


sync = {}
for mark, dur_key in (("play75", "dur75"), ("play130", "dur130")):
    vals = sorted(estimate(events[mark] + o, events[dur_key]) for o in (1.5, 2.5, 3.5, 4.5, 5.5))
    sync[mark] = round(vals[2] - 0.1, 3)
    print(mark, [round(v, 3) for v in vals], "->", sync[mark])

json.dump(sync, open("sync.json", "w"), indent=2)
