#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"
JS = ROOT / "public/assets/js/lyrics-ovh-r38-16.js"
OUTPUT_BLOCK = '    <div class="lyrics-ovh-output" data-lyrics-ovh-output>\n        <div class="lyrics-ovh-status" data-lyrics-ovh-status></div>\n        <div class="lyrics-ovh-results" data-lyrics-ovh-results></div>\n    </div>\n'

def main() -> int:
    if not TEMPLATE.is_file() or not JS.is_file():
        raise RuntimeError("R38.16 Lyrics.ovh files missing")

    template = TEMPLATE.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")

    # Remove the old search section below the textarea.
    template = re.sub(
        r'\s*<section\b[^>]*class="[^"]*\blyrics-ovh-search\b[^"]*"[^>]*>.*?</section>\s*',
        '\n',
        template,
        flags=re.S,
    )

    # Keep a single top toolbar.
    matches = list(re.finditer(
        r'<div\b[^>]*class="[^"]*\blyrics-ovh-toolbar\b[^"]*"[^>]*>.*?</div>',
        template,
        flags=re.S,
    ))
    if not matches:
        raise RuntimeError("Top Lyrics.ovh toolbar not found")
    for match in reversed(matches[1:]):
        template = template[:match.start()] + template[match.end():]

    # Remove any previous output containers.
    template = re.sub(
        r'\s*<div\b[^>]*data-lyrics-ovh-output[^>]*>.*?</div>\s*',
        '\n',
        template,
        flags=re.S,
    )
    template = re.sub(
        r'\s*<div\b[^>]*data-lyrics-ovh-status[^>]*>.*?</div>\s*',
        '\n',
        template,
        flags=re.S,
    )
    template = re.sub(
        r'\s*<div\b[^>]*data-lyrics-ovh-results[^>]*>.*?</div>\s*',
        '\n',
        template,
        flags=re.S,
    )

    # Place Lyrics.ovh status/results ABOVE the editable lyrics textarea.
    textarea_start = template.find('<textarea data-lyrics-source')
    if textarea_start < 0:
        raise RuntimeError("Lyrics textarea not found")
    template = template[:textarea_start] + OUTPUT_BLOCK + "\n" + template[textarea_start:]

    # The toolbar contains the input/button; status/results are document-level.
    old = """const input = root.querySelector('[data-lyrics-ovh-query]');
const button = root.querySelector('[data-lyrics-ovh-search]');
const resultsHost = root.querySelector('[data-lyrics-ovh-results]');
const status = root.querySelector('[data-lyrics-ovh-status]');
"""
    new = """const input = root.querySelector('[data-lyrics-ovh-query]');
const button = root.querySelector('[data-lyrics-ovh-search]');
const resultsHost = document.querySelector('[data-lyrics-ovh-results]');
const status = document.querySelector('[data-lyrics-ovh-status]');
"""
    if old in js:
        js = js.replace(old, new, 1)
    elif "const resultsHost = document.querySelector('[data-lyrics-ovh-results]');" not in js:
        raise RuntimeError("Lyrics.ovh JS selector anchor not found")

    # New asset URL guarantees the repaired JS is loaded.
    template, count = re.subn(
        r'(/assets/js/lyrics-ovh-r38-16\.js\?v=)[^"]+',
        r'\g<1>20260929r38_16c2',
        template,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Lyrics.ovh JS asset reference not found")

    TEMPLATE.write_text(template, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")

    print("R38_16C2_LYRICS_OVH_RESULTS_ABOVE_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
