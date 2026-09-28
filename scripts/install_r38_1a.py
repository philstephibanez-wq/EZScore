#!/usr/bin/env python3
from pathlib import Path
import sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
twig=repo/"templates"/"song"/"lyricslab.html.twig"
if not twig.is_file(): raise SystemExit(f"ABSENT: {twig}")
view=twig.read_text(encoding="utf-8")
for old in [
    "/assets/js/lyricslab-r37.js?v=20260928r37_0",
    "/assets/js/lyricslab-r37.js?v=20260928r38_0b",
    "/assets/js/lyricslab-r37.js?v=20260928r38_1",
]:
    view=view.replace(old,"/assets/js/lyricslab-r37.js?v=20260928r38_1a")
for old in [
    "/assets/css/lyricslab-r37.css?v=20260928r37_0",
    "/assets/css/lyricslab-r37.css?v=20260928r38_0b",
    "/assets/css/lyricslab-r37.css?v=20260928r38_1",
]:
    view=view.replace(old,"/assets/css/lyricslab-r37.css?v=20260928r38_1a")
view=view.replace(
    "Prompteur en lecture seule : section, accord courant fixe et paroles synchronisées mot à mot.",
    "Prompteur en lecture seule : accords et paroles défilent sous une zone de lecture fixe."
)
twig.write_text(view,encoding="utf-8",newline="\n")
print("R38_1A_INSTALL_OK")
