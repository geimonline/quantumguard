#!/usr/bin/env python3
"""Grab still frames from the recorded demo video using Chromium (no ffmpeg needed)."""
import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

VIDEO = Path(__file__).parent / "video" / "quantumguard-demo.webm"
OUT = Path(__file__).parent / "frames"

HTML = """<!doctype html><meta charset=utf-8>
<body style="margin:0;background:#000">
<video id=v muted playsinline preload=auto
       style="width:1600px;height:900px;display:block"></video>
</body>"""


def main(times):
    OUT.mkdir(exist_ok=True)
    data_uri = "data:video/webm;base64," + base64.b64encode(VIDEO.read_bytes()).decode()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 1600, "height": 900})
        page.set_content(HTML)
        page.evaluate(
            """(src) => new Promise((res, rej) => {
                const v = document.getElementById('v');
                v.addEventListener('loadeddata', () => res(true), {once: true});
                v.addEventListener('error', () => rej('load error'), {once: true});
                v.src = src;
            })""",
            data_uri,
        )
        for t in times:
            page.evaluate("t => new Promise(r => {"
                          "  const v = document.getElementById('v');"
                          "  const f = () => { v.removeEventListener('seeked', f); setTimeout(r, 250); };"
                          "  v.addEventListener('seeked', f); v.currentTime = t;"
                          "})", float(t))
            page.screenshot(path=str(OUT / f"t{float(t):05.1f}.png"))
            print("frame", t, flush=True)
        b.close()


if __name__ == "__main__":
    main([float(x) for x in sys.argv[1:]] or [2, 8, 16, 24, 31])
