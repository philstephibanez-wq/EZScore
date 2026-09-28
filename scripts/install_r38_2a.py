#!/usr/bin/env python3
from pathlib import Path
import re
import sys

repo=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
twig=repo/"templates"/"song"/"lyricslab.html.twig"

if not twig.is_file():
    raise SystemExit(f"ABSENT: {twig}")

view=twig.read_text(encoding="utf-8")
view=re.sub(
    r'/assets/js/lyricslab-r37\.js\?v=[^"\']+',
    '/assets/js/lyricslab-r37.js?v=20260928r38_2a',
    view,
)
twig.write_text(view,encoding="utf-8",newline="\n")
print("R38_2A_INSTALL_OK")
