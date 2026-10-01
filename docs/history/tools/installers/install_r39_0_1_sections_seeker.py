#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
HERE=Path(__file__).resolve().parent.parent
JS=ROOT/"public/assets/js/lyricslab-timeline-r39.js"
TWIG=ROOT/"templates/song/lyricslab.html.twig"
CSS=ROOT/"public/assets/css/lyricslab-r37.css"
PATCH=HERE/"patches/lyricslab-r39-0-1-sections-seeker.js"
CSSPATCH=HERE/"patches/lyricslab-r39-0-1.css.txt"

for p in (JS,TWIG,CSS,PATCH,CSSPATCH):
    if not p.is_file(): raise RuntimeError(f"Missing prerequisite: {p}")

js=JS.read_text(encoding="utf-8")
twig=TWIG.read_text(encoding="utf-8")
css=CSS.read_text(encoding="utf-8")
addon=PATCH.read_text(encoding="utf-8")
cssaddon=CSSPATCH.read_text(encoding="utf-8")

if "R39.0.1 — restore sections + manual seeker" not in js:
    js=js.rstrip()+"\n\n"+addon.rstrip()+"\n"

if "R39.0.1 sections + manual seek" not in css:
    css=css.rstrip()+"\n\n"+cssaddon.rstrip()+"\n"

twig=twig.replace(
    '/assets/css/lyricslab-r37.css?v=20260929r39_0',
    '/assets/css/lyricslab-r37.css?v=20260929r39_0_1'
)
twig=twig.replace(
    '/assets/js/lyricslab-timeline-r39.js?v=20260929r39_0',
    '/assets/js/lyricslab-timeline-r39.js?v=20260929r39_0_1'
)

for needle in ("data-section-nav","data-lyrics-manual-seeker","ezscore:request-seek","sectionsRestored='r39.0.1'"):
    if needle not in js: raise RuntimeError(f"validation failed: {needle}")
if "lyricslab-timeline-r39.js?v=20260929r39_0_1" not in twig:
    raise RuntimeError("cache-bust validation failed")

JS.write_text(js,encoding="utf-8",newline="\n")
TWIG.write_text(twig,encoding="utf-8",newline="\n")
CSS.write_text(css,encoding="utf-8",newline="\n")
print("R39_0_1_SECTIONS_SEEKER_INSTALL_OK")
