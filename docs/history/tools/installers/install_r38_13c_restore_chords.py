#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
JS = ROOT / "public" / "assets" / "js" / "lyricslab-r37.js"
TWIG = ROOT / "templates" / "song" / "lyricslab.html.twig"

def main() -> int:
    if not JS.is_file():
        raise SystemExit(f"Missing: {JS}")
    if not TWIG.is_file():
        raise SystemExit(f"Missing: {TWIG}")

    src = JS.read_text(encoding="utf-8")

    if "R38.13c: restore chord lane runtime declaration" in src:
        print("R38_13C_JS_ALREADY_INSTALLED")
    else:
        if "R38.13b: time-signature agnostic continuous projection" not in src:
            raise RuntimeError("R38.13b not found; refusing to patch unexpected LyricsLab")

        broken = ";left=xBeat(i),next="
        fixed = ";/* R38.13c: restore chord lane runtime declaration */const left=xBeat(i),next="
        count = src.count(broken)
        if count != 1:
            raise RuntimeError(f"broken chord-lane anchor: expected 1, found {count}")
        src = src.replace(broken, fixed, 1)

        JS.write_text(src, encoding="utf-8")
        print("R38_13C_JS_OK")

    twig = TWIG.read_text(encoding="utf-8")
    if "20260928r38_13c" not in twig:
        twig, count = re.subn(
            r"(/assets/js/lyricslab-r37\.js\?v=)[^\"']+",
            r"\g<1>20260928r38_13c",
            twig,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Twig cache buster: expected 1, found {count}")
        TWIG.write_text(twig, encoding="utf-8")
        print("R38_13C_TWIG_OK")
    else:
        print("R38_13C_TWIG_ALREADY_INSTALLED")

    print("R38_13C_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
