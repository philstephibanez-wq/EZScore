#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"
JS = ROOT / "public/assets/js/lyrics-history-r38-15.js"

def main() -> int:
    if not TEMPLATE.is_file() or not JS.is_file():
        raise RuntimeError("LyricsLab R38.15 files missing")

    js = JS.read_text(encoding="utf-8")
    if "confirm(" in js or "alert(" in js or "prompt(" in js:
        raise RuntimeError("Native browser dialog still present in lyrics-history-r38-15.js")
    if "function ezConfirm(" not in js:
        raise RuntimeError("Custom EZScore modal not present in lyrics-history-r38-15.js")

    template = TEMPLATE.read_text(encoding="utf-8")

    # Force a new immutable asset URL. This is deliberately independent of browser/CDN cache.
    template, js_count = re.subn(
        r'(/assets/js/lyrics-history-r38-15\.js\?v=)[^"]+',
        r'\g<1>20260929r38_15d',
        template,
        count=1,
    )
    template, css_count = re.subn(
        r'(/assets/css/lyrics-history-r38-15\.css\?v=)[^"]+',
        r'\g<1>20260929r38_15d',
        template,
        count=1,
    )

    if js_count != 1:
        raise RuntimeError(f"Expected exactly one lyrics-history JS asset reference, found {js_count}")
    if css_count != 1:
        raise RuntimeError(f"Expected exactly one lyrics-history CSS asset reference, found {css_count}")

    TEMPLATE.write_text(template, encoding="utf-8", newline="\n")
    print("R38_15D_FORCE_ASSET_REFRESH_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
