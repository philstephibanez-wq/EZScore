#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "public/assets/js/stems-mixer.js").read_text(encoding="utf-8")
css = (ROOT / "public/assets/css/stems.css").read_text(encoding="utf-8")

assert "track.status.dataset.state = state || 'idle';" in js
assert "/* R39.2A compact readable track state */" in css
assert "min-width:34px!important" in css
assert "max-width:52px!important" in css

# Critical non-regression: keep R29/R39.2 mixer proportions exactly.
assert ".stem-mixer-grid{grid-template-columns:minmax(170px,220px) 92px minmax(260px,1fr);gap:14px}" in css

for rel in [
    "templates/stems/index.html.twig",
    "templates/song/chordslab.html.twig",
    "templates/song/lyricslab.html.twig",
]:
    t = (ROOT / rel).read_text(encoding="utf-8")
    assert "/assets/css/stems.css?v=20260929r39_2a" in t
    assert "/assets/js/stems-mixer.js?v=20260929r39_2a" in t

print("R39.2A_TRACK_READY_BADGE_CONTRACT_OK")
