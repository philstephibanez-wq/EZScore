#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
HERE=Path(__file__).resolve().parent.parent

twig=ROOT/"templates/song/lyricslab.html.twig"
cssfile=ROOT/"public/assets/css/lyricslab-r37.css"
jsfile=ROOT/"public/assets/js/lyricslab-collision-r39-2.js"

for p in (twig,cssfile):
    if not p.is_file(): raise RuntimeError(f"Missing prerequisite: {p}")

t=twig.read_text(encoding="utf-8")
c=cssfile.read_text(encoding="utf-8")
addon_js=(HERE/"patches/lyricslab-collision-r39-2.js").read_text(encoding="utf-8")
addon_css=(HERE/"patches/lyricslab-collision-r39-2.css.txt").read_text(encoding="utf-8")

# R39 baseline must already be installed.
for needle in ["lyricslab-timeline-r39.js","ezscore-timeline-core-r39.js"]:
    if needle not in t:
        raise RuntimeError(f"R39 baseline missing: {needle}")

jsfile.write_text(addon_js,encoding="utf-8",newline="\n")

if "EZScore R39.2 — visual-only collision handling" not in c:
    c=c.rstrip()+"\n\n"+addon_css.rstrip()+"\n"

tag='<script src="/assets/js/lyricslab-collision-r39-2.js?v=20260929r39_2"></script>'
if tag not in t:
    anchor='</script>\n{% endblock %}'
    # safer: append before javascripts endblock using known last script
    last='<script src="/assets/js/lyrics-dirty-guard-r38-16j.js?v=20260929r38_16m2"></script>'
    if last not in t:
        raise RuntimeError("LyricsLab final script anchor not found")
    t=t.replace(last,last+"\n"+tag,1)

t=t.replace('/assets/css/lyricslab-r37.css?v=20260929r39_0_1','/assets/css/lyricslab-r37.css?v=20260929r39_2')
t=t.replace('/assets/css/lyricslab-r37.css?v=20260929r39_0','/assets/css/lyricslab-r37.css?v=20260929r39_2')

for needle in ["lyricslab-collision-r39-2.js?v=20260929r39_2","lyricslab-r37.css?v=20260929r39_2"]:
    if needle not in t: raise RuntimeError(f"cache bust validation failed: {needle}")

twig.write_text(t,encoding="utf-8",newline="\n")
cssfile.write_text(c,encoding="utf-8",newline="\n")

print("R39_2_LYRIC_COLLISION_LAYOUT_INSTALL_OK")
