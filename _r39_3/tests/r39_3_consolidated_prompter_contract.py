#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()

js=(ROOT/"public/assets/js/chordslab.js").read_text(encoding="utf-8")
css=(ROOT/"public/assets/css/chordslab.css").read_text(encoding="utf-8")
twig=(ROOT/"templates/song/chordslab.html.twig").read_text(encoding="utf-8")
focus=(ROOT/"public/assets/js/components/ezscore-focus-track.js").read_text(encoding="utf-8")
diag=(ROOT/"public/assets/js/components/ezscore-chord-diagram.js").read_text(encoding="utf-8")
diagcss=(ROOT/"public/assets/css/components/ezscore-chord-diagram.css").read_text(encoding="utf-8")

assert "class EZScoreFocusTrack" in focus
assert "translate3d(" in focus
assert "scrollLeft" not in focus
assert "scrollBy(" not in focus
assert "scrollTo(" not in focus

assert "window.EZScoreChordDiagram" in diag
assert "SHAPES" in diag
assert "background:#fff" in diagcss
assert "width:150px" in diagcss

assert "data-chordslab-measures-track" in js
assert "track.appendChild(box)" in js
assert "new window.EZScoreFocusTrack(measuresEl" in js
assert "alignCurrentTime(slot,seq,ms)" in js
assert "(ms-t0)/(t1-t0)" in js
assert "window.EZScoreChordDiagram.render(diagramEl,chord)" in js
assert "const SHAPES=" not in js

assert "/* R39.3 — consolidated fixed-focus prompter." in css
assert "--chord-focus-x:25%" in css
assert "overflow-x:hidden!important" in css
assert ".chordslab-measures-track" in css
assert "transition:none!important" in css

assert "Profil affiché" not in twig
assert "/assets/css/components/ezscore-chord-diagram.css?v=20260930r39_3" in twig
assert "/assets/js/components/ezscore-chord-diagram.js?v=20260930r39_3" in twig
assert "/assets/js/components/ezscore-focus-track.js?v=20260930r39_3" in twig
assert "/assets/js/chordslab.js?v=20260930r39_3" in twig

print("R39_3_CONSOLIDATED_PROMPTER_CONTRACT_OK")
