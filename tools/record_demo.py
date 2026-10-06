"""Record the Linger demo (silent video) with Playwright.

Run from a build directory: python record_demo.py <audio-file> [url]
Writes video/<name>.webm and events.json (wall-clock marks for playback starts).
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

AUDIO = sys.argv[1] if len(sys.argv) > 1 else "podcast-clip.m4a"
URL = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5056/"
W, H = 1440, 900

OVERLAY_JS = """
window.addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.id = '__cursor';
  c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:99999;pointer-events:none;' +
    'transform:translate(-3px,-2px);transition:transform .08s';
  c.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M3 2l7 19 2.5-8L21 10z" fill="#1b2340" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', () => c.style.transform = 'translate(-3px,-2px) scale(.8)', true);
  document.addEventListener('mouseup',   () => c.style.transform = 'translate(-3px,-2px)', true);

  const cap = document.createElement('div');
  cap.id = '__caption';
  cap.style.cssText = 'position:fixed;left:50%;top:22px;transform:translateX(-50%);z-index:99998;' +
    'font:600 17px "DM Sans",sans-serif;color:#1b2340;background:#fff;border:1px solid #e6ebf7;box-shadow:0 10px 30px -10px rgba(59,108,255,.35);' +
    'padding:10px 22px;border-radius:999px;opacity:0;transition:opacity .35s;white-space:nowrap;letter-spacing:.02em';
  document.body.appendChild(cap);
  window.__caption = (t) => {
    cap.style.opacity = 0;
    setTimeout(() => { cap.textContent = t; cap.style.opacity = t ? 1 : 0; }, t && cap.textContent ? 350 : 0);
  };
});
"""


def main():
    events = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
            record_video_dir="video",
            record_video_size={"width": W, "height": H},
        )
        ctx.add_init_script(OVERLAY_JS)
        page = ctx.new_page()
        t0 = time.monotonic()
        mark = lambda k: events.__setitem__(k, round(time.monotonic() - t0, 3))

        page.goto(URL)
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.mouse.move(W - 200, H - 150)
        page.wait_for_timeout(3300)  # let the intro screen play out
        page.evaluate("__caption('Linger — change tempo, keep pitch')")
        page.wait_for_timeout(2000)

        def glide(x, y, steps=25):
            page.mouse.move(x, y, steps=steps)

        def center(sel):
            b = page.locator(sel).bounding_box()
            return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

        # 1. choose a file
        page.evaluate("__caption('1 · Choose an MP3, M4A or WAV file')")
        glide(*center("#drop-zone"))
        page.wait_for_timeout(700)
        page.mouse.down(); page.mouse.up()
        page.set_input_files("#audio-file", AUDIO)
        page.wait_for_timeout(1800)

        # 2. drag slider 90 -> 75
        page.evaluate("__caption('2 · Drag to set the target speed')")
        sb = page.locator("#speed").bounding_box()
        thumb = 18
        xfor = lambda v: sb["x"] + thumb / 2 + (sb["width"] - thumb) * (v - 70) / 60
        sy = sb["y"] + sb["height"] / 2
        glide(xfor(90), sy)
        page.wait_for_timeout(400)
        page.mouse.down()
        page.mouse.move(xfor(75), sy, steps=40)
        page.mouse.up()
        # nudge to an exact value if the drag landed slightly off
        for _ in range(5):
            v = int(page.input_value("#speed"))
            if v == 75:
                break
            page.keyboard.press("ArrowLeft" if v > 75 else "ArrowRight")
        page.wait_for_timeout(1200)

        # 3. process & play
        page.evaluate("__caption('3 · Process & Play — ffmpeg slows it to 75%')")
        glide(*center("#submit-btn"))
        page.wait_for_timeout(400)
        page.click("#submit-btn")
        page.wait_for_function("!document.getElementById('player').paused && document.getElementById('player').currentTime > 0")
        mark("play75")
        page.mouse.move(W - 160, H - 120, steps=20)
        dur75 = page.evaluate("document.getElementById('player').duration")
        page.wait_for_timeout(int(dur75 * 1000) + 600)

        # 4. faster: click 130% tick, process again
        page.evaluate("__caption('Tap a preset — now try 130% faster')")
        glide(*center(".speed-ticks span[data-speed='130']"))
        page.wait_for_timeout(500)
        page.click(".speed-ticks span[data-speed='130']")
        page.wait_for_timeout(1000)
        glide(*center("#submit-btn"))
        page.wait_for_timeout(300)
        page.click("#submit-btn")
        page.wait_for_function("document.getElementById('status').textContent.includes('130') && !document.getElementById('player').paused && document.getElementById('player').currentTime > 0")
        mark("play130")
        page.mouse.move(W - 160, H - 120, steps=20)
        dur130 = page.evaluate("document.getElementById('player').duration")
        page.wait_for_timeout(int(dur130 * 1000) + 500)

        page.evaluate("__caption('Linger · 70–130% · pitch preserved')")
        page.wait_for_timeout(2500)
        mark("end")

        video_path = page.video.path()
        ctx.close()
        browser.close()

    events["video"] = video_path
    events["dur75"], events["dur130"] = dur75, dur130
    json.dump(events, open("events.json", "w"), indent=2)
    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
