import io
import os
import subprocess
import tempfile

from flask import Flask, jsonify, render_template_string, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

ALLOWED_EXTENSIONS = {"mp3", "m4a", "wav"}

MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
}

MIN_SPEED = 70
MAX_SPEED = 130


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Linger</title>
<meta name="theme-color" content="#ffffff">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Linger">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="/static/icon-192.png">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:        #ffffff;
    --surface:   #ffffff;
    --border:    #e6ebf7;
    --track:     #e8edfa;
    --accent:    #3b6cff;
    --accent-dim:#d6e0ff;
    --tint:      #f3f6ff;
    --text:      #1b2340;
    --muted:     #8a93ad;
    --success:   #12b886;
    --error:     #f03e5e;
    --grad:      linear-gradient(135deg, #36c6ff 0%, #3b6cff 50%, #6a4dff 100%);
    --grad-h:    linear-gradient(90deg,  #36c6ff 0%, #3b6cff 50%, #6a4dff 100%);
    --glow:      0 10px 24px -8px rgba(59, 108, 255, 0.55);
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-weight: 400;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    padding-top:    max(2rem, env(safe-area-inset-top));
    padding-bottom: max(2rem, env(safe-area-inset-bottom));
    -webkit-tap-highlight-color: transparent;
  }

  /* soft blue glows in the corners */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
      radial-gradient(600px circle at 0% 0%,     rgba(54, 198, 255, 0.10), transparent 60%),
      radial-gradient(700px circle at 100% 100%, rgba(106, 77, 255, 0.10), transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  .card {
    position: relative;
    z-index: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 3rem 3.5rem;
    width: 100%;
    max-width: 520px;
    box-shadow: 0 40px 80px -30px rgba(59, 108, 255, 0.28), 0 2px 8px rgba(27, 35, 64, 0.04);
  }

  .header {
    margin-bottom: 2.5rem;
  }

  .logo {
    font-family: 'Poppins', sans-serif;
    font-weight: 700;
    font-size: 2.6rem;
    letter-spacing: -0.02em;
    line-height: 1.1;
    padding-bottom: 0.12em;   /* room for descenders under background-clip: text */
    margin-bottom: -0.12em;
    background: var(--grad-h);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .tagline {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-top: 0.35rem;
  }

  .divider {
    height: 1px;
    background: var(--border);
    margin: 1.5rem 0;
  }

  label {
    display: block;
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    margin-bottom: 0.6rem;
  }

  /* Drop zone */
  .drop-zone {
    border: 1.5px dashed #c9d6ff;
    border-radius: 18px;
    background: var(--tint);
    padding: 2.25rem 1.5rem;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    margin-bottom: 1.5rem;
    position: relative;
  }

  .drop-zone:hover,
  .drop-zone.dragover {
    border-color: var(--accent);
    background: #eaf0ff;
  }

  .drop-zone input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }

  .drop-icon {
    width: 56px;
    height: 56px;
    margin: 0 auto 0.85rem;
    border-radius: 50%;
    background: var(--grad);
    box-shadow: var(--glow);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .drop-icon svg { width: 24px; height: 24px; }

  .drop-text {
    font-size: 0.9rem;
    color: var(--muted);
  }

  .drop-text strong {
    color: var(--accent);
    font-weight: 600;
  }

  .file-types {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--muted);
    margin-top: 0.4rem;
    letter-spacing: 0.08em;
  }

  #file-name {
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--success);
    min-height: 1.2em;
    word-break: break-all;
  }

  /* Speed slider */
  .speed-slider {
    margin-bottom: 2rem;
  }

  .speed-readout {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 0.9rem;
    font-family: 'JetBrains Mono', monospace;
  }

  #speed-value {
    font-family: 'Poppins', sans-serif;
    font-size: 1.9rem;
    font-weight: 600;
    line-height: 1;
    background: var(--grad-h);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  #speed-desc {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--accent);
    background: var(--tint);
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
  }

  input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background: var(--track);
    outline: none;
    cursor: pointer;
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #fff;
    border: 5px solid var(--accent);
    box-shadow: var(--glow);
    transition: transform 0.1s;
  }

  input[type="range"]::-moz-range-thumb {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #fff;
    border: 5px solid var(--accent);
    box-shadow: var(--glow);
  }

  input[type="range"]:active::-webkit-slider-thumb { transform: scale(1.15); }

  input[type="range"]:focus-visible::-webkit-slider-thumb {
    box-shadow: var(--glow), 0 0 0 6px rgba(59, 108, 255, 0.18);
  }

  .speed-ticks {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
  }

  .speed-ticks span { cursor: pointer; }
  .speed-ticks span:hover { color: var(--accent); }

  /* Touch devices: bigger slider, tap wording */
  .touch-only { display: none; }

  @media (pointer: coarse) {
    .touch-only   { display: inline; }
    .pointer-only { display: none; }

    input[type="range"] { height: 8px; border-radius: 4px; }

    input[type="range"]::-webkit-slider-thumb { width: 30px; height: 30px; }
    input[type="range"]::-moz-range-thumb     { width: 30px; height: 30px; }

    .speed-ticks { font-size: 0.75rem; margin-top: 0.4rem; }
    .speed-ticks span { padding: 0.5rem 0.25rem; }
  }

  /* Narrow screens */
  @media (max-width: 540px) {
    body {
      padding-left:  max(0.75rem, env(safe-area-inset-left));
      padding-right: max(0.75rem, env(safe-area-inset-right));
    }

    .card {
      padding: 2rem 1.4rem;
      box-shadow: 0 24px 48px -24px rgba(59, 108, 255, 0.3), 0 2px 8px rgba(27, 35, 64, 0.04);
    }

    .header { margin-bottom: 1.75rem; }
    .logo   { font-size: 2.5rem; }

    .drop-zone { padding: 1.75rem 1rem; }

    .submit-btn { padding: 1.1rem; }
  }

  /* Submit */
  .submit-btn {
    width: 100%;
    padding: 1rem;
    background: var(--grad);
    border: none;
    border-radius: 999px;
    color: #fff;
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    cursor: pointer;
    box-shadow: var(--glow);
    transition: opacity 0.2s, transform 0.1s, box-shadow 0.2s;
  }

  .submit-btn:hover:not(:disabled) { box-shadow: 0 14px 30px -8px rgba(59, 108, 255, 0.65); transform: translateY(-1px); }
  .submit-btn:active:not(:disabled) { transform: scale(0.98); }
  .submit-btn:disabled { opacity: 0.4; box-shadow: none; cursor: not-allowed; }

  /* Status messages */
  #status {
    margin-top: 1.2rem;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.85rem;
    text-align: center;
    min-height: 1.2em;
  }

  #status.processing { color: var(--accent); }
  #status.error      { color: var(--error); }
  #status.done       { color: var(--success); }

  .spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid var(--accent-dim);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* Player */
  #player {
    display: none;
    width: 100%;
    margin-top: 1.2rem;
    color-scheme: light;
  }

  #player.ready { display: block; }

  /* Intro: logo + wordmark, then cross-fade into the card */
  #intro {
    position: fixed;
    inset: 0;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1.4rem;
    pointer-events: none;
    animation: intro-out 0.45s ease-in 2s forwards;
  }

  #intro .intro-logo,
  #intro .intro-wordmark {
    animation: intro-in 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  #intro .intro-wordmark { animation-delay: 0.15s; }

  .intro-logo {
    width: 104px;
    height: 104px;
    border-radius: 28px;
    background: var(--grad);
    box-shadow: 0 24px 48px -16px rgba(59, 108, 255, 0.55);
    overflow: hidden;
  }

  .intro-logo svg { width: 100%; height: 100%; display: block; }

  .intro-logo rect {
    fill: #fff;
    transform-box: fill-box;
    transform-origin: center;
    animation: intro-bar 0.9s ease-in-out infinite alternate;
  }

  .intro-wordmark {
    font-family: 'Poppins', sans-serif;
    font-weight: 700;
    font-size: 3.2rem;
    letter-spacing: -0.02em;
    line-height: 1.1;
    padding-bottom: 0.12em;
    margin-bottom: -0.12em;
    background: var(--grad-h);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .card { animation: card-in 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) 2.45s both; }

  @keyframes intro-in  { from { opacity: 0; transform: translateY(14px) scale(0.94); } }
  @keyframes intro-out { to   { opacity: 0; transform: scale(1.04); visibility: hidden; } }
  @keyframes intro-bar { from { transform: scaleY(0.6); } }
  @keyframes card-in   { from { opacity: 0; transform: translateY(18px); } }

  @media (max-width: 540px) {
    .intro-logo     { width: 88px; height: 88px; border-radius: 24px; }
    .intro-wordmark { font-size: 2.6rem; }
  }

  @media (prefers-reduced-motion: reduce) {
    #intro { animation-delay: 1s; animation-duration: 0.3s; }
    #intro .intro-logo, #intro .intro-wordmark, .intro-logo rect { animation: none; }
    .card { animation: card-in 0.3s ease 1s both; }
  }
</style>
</head>
<body>
<div id="intro" aria-hidden="true">
  <div class="intro-logo"><svg viewBox="0 0 512 512"><rect x="113" y="213" width="17" height="86" rx="8.5" style="animation-delay:0.00s"/><rect x="146" y="177" width="17" height="158" rx="8.5" style="animation-delay:0.09s"/><rect x="180" y="134" width="17" height="244" rx="8.5" style="animation-delay:0.18s"/><rect x="214" y="170" width="17" height="172" rx="8.5" style="animation-delay:0.27s"/><rect x="248" y="113" width="17" height="286" rx="8.5" style="animation-delay:0.36s"/><rect x="281" y="156" width="17" height="200" rx="8.5" style="animation-delay:0.45s"/><rect x="315" y="192" width="17" height="129" rx="8.5" style="animation-delay:0.54s"/><rect x="349" y="149" width="17" height="215" rx="8.5" style="animation-delay:0.63s"/><rect x="383" y="206" width="16" height="100" rx="8" style="animation-delay:0.72s"/></svg></div>
  <div class="intro-wordmark">Linger</div>
</div>
<div class="card">
  <div class="header">
    <div class="logo">Linger</div>
    <div class="tagline">Tempo change // Pitch preserved</div>
  </div>
  <div class="divider"></div>

  <label>Audio File</label>
  <div class="drop-zone" id="drop-zone">
    <input type="file" id="audio-file" accept=".mp3,.m4a,.wav">
    <span class="drop-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg></span>
    <div class="drop-text">
      <span class="pointer-only"><strong>Click to choose</strong> or drag and drop</span>
      <span class="touch-only"><strong>Tap to choose a file</strong></span>
    </div>
    <div class="file-types">MP3 &nbsp;·&nbsp; M4A &nbsp;·&nbsp; WAV</div>
    <div id="file-name"></div>
  </div>

  <label>Target Speed</label>
  <div class="speed-slider">
    <div class="speed-readout">
      <span id="speed-value">90%</span>
      <span id="speed-desc">Slower</span>
    </div>
    <input type="range" id="speed" min="70" max="130" step="1" value="90">
    <div class="speed-ticks">
      <span data-speed="70">70%</span>
      <span data-speed="100">100%</span>
      <span data-speed="130">130%</span>
    </div>
  </div>

  <button class="submit-btn" id="submit-btn" disabled>Process &amp; Play</button>
  <div id="status"></div>
  <audio id="player" controls></audio>
</div>

<script>
  let selectedSpeed = "90";
  let selectedFile  = null;

  const fileInput  = document.getElementById("audio-file");
  const fileNameEl = document.getElementById("file-name");
  const submitBtn  = document.getElementById("submit-btn");
  const statusEl   = document.getElementById("status");
  const dropZone   = document.getElementById("drop-zone");
  const player     = document.getElementById("player");
  let playerUrl    = null;

  // Speed slider
  const speedInput = document.getElementById("speed");
  const speedValEl = document.getElementById("speed-value");
  const speedDesc  = document.getElementById("speed-desc");

  function updateSpeed() {
    const v = Number(speedInput.value);
    selectedSpeed = String(v);
    speedValEl.textContent = v + "%";
    speedDesc.textContent = v < 100 ? "Slower" : v > 100 ? "Faster" : "Original";
    const pct = (v - speedInput.min) / (speedInput.max - speedInput.min) * 100;
    speedInput.style.background =
      `var(--grad-h) 0 0 / ${pct}% 100% no-repeat, var(--track)`;
  }

  speedInput.addEventListener("input", updateSpeed);
  document.querySelectorAll(".speed-ticks span").forEach(t => {
    t.addEventListener("click", () => { speedInput.value = t.dataset.speed; updateSpeed(); });
  });
  updateSpeed();

  // File selection
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      selectedFile = fileInput.files[0];
      fileNameEl.textContent = selectedFile.name;
      submitBtn.disabled = false;
      statusEl.textContent = "";
      statusEl.className = "";
    }
  });

  // Drag and drop
  dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      const ext = file.name.split(".").pop().toLowerCase();
      if (!["mp3","m4a","wav"].includes(ext)) {
        statusEl.textContent = "Unsupported file type.";
        statusEl.className = "error";
        return;
      }
      selectedFile = file;
      fileNameEl.textContent = file.name;
      submitBtn.disabled = false;
      statusEl.textContent = "";
      statusEl.className = "";
    }
  });

  // Submit
  submitBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    submitBtn.disabled = true;
    statusEl.innerHTML = '<span class="spinner"></span> Processing...';
    statusEl.className = "processing";

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("speed", selectedSpeed);

    try {
      const response = await fetch("/process", { method: "POST", body: formData });

      if (!response.ok) {
        const data = await response.json();
        statusEl.textContent = "Error: " + (data.error || "Something went wrong.");
        statusEl.className = "error";
        submitBtn.disabled = false;
        return;
      }

      const blob = await response.blob();

      if (playerUrl) URL.revokeObjectURL(playerUrl);
      playerUrl = URL.createObjectURL(blob);
      player.src = playerUrl;
      player.classList.add("ready");

      statusEl.textContent = `Playing at ${selectedSpeed}%`;
      statusEl.className = "done";

      try {
        await player.play();
      } catch (e) {
        statusEl.textContent = "Ready — press play.";
      }
    } catch (err) {
      statusEl.textContent = "Network error. Is the server running?";
      statusEl.className = "error";
    } finally {
      submitBtn.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "Linger",
        "short_name": "Linger",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#ffffff",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    response = jsonify(data)
    response.mimetype = "application/manifest+json"
    return response


@app.route("/process", methods=["POST"])
def process():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    speed = request.form.get("speed", "90")

    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use MP3, M4A or WAV."}), 400

    if not speed.isdigit() or not MIN_SPEED <= int(speed) <= MAX_SPEED:
        return jsonify({"error": f"Speed must be between {MIN_SPEED} and {MAX_SPEED}."}), 400

    speed = str(int(speed))

    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    direction = "slower" if int(speed) < 100 else "faster" if int(speed) > 100 else "original"
    output_filename = f"{name}-{speed}-{direction}{ext}"
    atempo = float(speed) / 100.0
    mime = MIME_MAP.get(ext.lower(), "audio/mpeg")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = os.path.join(tmpdir, filename)
        output_path = os.path.join(tmpdir, output_filename)

        file.save(input_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter:a", f"atempo={atempo}",
            "-vn",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({
                "error": "ffmpeg processing failed.",
                "details": result.stderr[-500:],
            }), 500

        with open(output_path, "rb") as f:
            audio_data = f.read()

    return send_file(
        io.BytesIO(audio_data),
        as_attachment=False,
        download_name=output_filename,
        mimetype=mime,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5056)
