"""Regenerate the PWA icons in ../static and the iOS app icon: white waveform bars on the blue gradient.

    python make_icons.py
"""
import os

from PIL import Image, ImageDraw

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
IOS_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ios", "Linger",
                        "Assets.xcassets", "AppIcon.appiconset")
S = 512 * 4  # supersample, then downscale for smooth edges

# (x0, x1, y0, y1) of each bar on a 512px canvas, same geometry as the intro logo
BARS = [(113, 129, 213, 298), (146, 162, 177, 334), (180, 196, 134, 377), (214, 230, 170, 341),
        (248, 264, 113, 398), (281, 297, 156, 355), (315, 331, 192, 320), (349, 365, 149, 363),
        (383, 398, 206, 305)]
STOPS = [(0, (0x36, 0xc6, 0xff)), (0.5, (0x3b, 0x6c, 0xff)), (1, (0x6a, 0x4d, 0xff))]


def color(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))


strip = Image.new("RGB", (S * 2, 1))
for x in range(S * 2):
    strip.putpixel((x, 0), color(x / (S * 2 - 1)))
img = strip.resize((S * 2, S * 2)).rotate(-45, resample=Image.BICUBIC).crop((S // 2, S // 2, S // 2 + S, S // 2 + S))

draw = ImageDraw.Draw(img)
k = S / 512
for x0, x1, y0, y1 in BARS:
    w = (x1 - x0 + 1) * k
    draw.rounded_rectangle([x0 * k, y0 * k, (x1 + 1) * k, (y1 + 1) * k], radius=w / 2, fill="white")

base = img.resize((512, 512), Image.LANCZOS)
for name, size in (("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180)):
    base.resize((size, size), Image.LANCZOS).save(os.path.join(STATIC, name))
    print("wrote", name)

# iOS app icon: one 1024px opaque PNG; iOS applies the rounded mask itself.
img.resize((1024, 1024), Image.LANCZOS).save(os.path.join(IOS_ICON, "icon-1024.png"))
print("wrote ios icon-1024.png")
