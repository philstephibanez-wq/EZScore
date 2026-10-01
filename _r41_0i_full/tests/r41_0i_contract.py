#!/usr/bin/env python3
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
rd=lambda p:(ROOT/p).read_text(encoding="utf-8-sig")

cj=rd("public/assets/js/chordslab.js")
cc=rd("public/assets/css/chordslab.css")
ct=rd("templates/song/chordslab.html.twig")
lj=rd("public/assets/js/lyricslab-timeline-r39.js")
lc=rd("public/assets/css/lyricslab-r37.css")
lt=rd("templates/song/lyricslab.html.twig")

assert "function syncDiagramLayout()" in cj
assert "diagramToggle?.addEventListener('change',syncDiagramLayout);" in cj
assert "highlightAt(lastPlaybackSeconds);" in cj
assert "stageEl?.classList.toggle('is-diagram-collapsed',!expanded);" in cj
assert ".chordslab-stage.is-diagram-collapsed" in cc
assert "padding-top:0!important;" in cc
assert "min-height:0!important;" in cc
assert "padding-top:164px!important;" in cc
assert "min-height:220px;" in cc

assert "const diagramExpanded=Boolean(diagramToggle?.checked);" in lj
assert "stage.classList.toggle('is-diagram-collapsed',!diagramExpanded);" in lj
assert "stageShell?.classList.toggle('is-diagram-collapsed',!diagramExpanded);" in lj
assert "[data-lyricslab] .r39-shared-timeline.is-diagram-collapsed" in lc
assert "height:236px!important;" in lc
assert "top:18px!important;" in lc
assert "top:128px!important;" in lc
assert "height:392px!important;" in lc
assert "top:174px!important;" in lc
assert "top:284px!important;" in lc

assert "EZScoreTimelineCoreR39" in lj
assert "ezscore:audio-timeupdate" in lj
assert "ezscore:request-seek" in lj
assert "new Audio(" not in cj and "new AudioContext" not in cj
assert "new Audio(" not in lj and "new AudioContext" not in lj

assert "/assets/css/chordslab.css?v=20261001r41_0i" in ct
assert "/assets/js/chordslab.js?v=20261001r41_0i" in ct
assert "/assets/css/lyricslab-r37.css?v=20261001r41_0i" in lt
assert "/assets/js/lyricslab-timeline-r39.js?v=20261001r41_0i" in lt

p=subprocess.run(["git","diff","--name-only"],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",check=True)
changed={x.strip() for x in p.stdout.splitlines() if x.strip()}
expected={
 "public/assets/css/chordslab.css",
 "public/assets/css/lyricslab-r37.css",
 "public/assets/js/chordslab.js",
 "public/assets/js/lyricslab-timeline-r39.js",
 "templates/song/chordslab.html.twig",
 "templates/song/lyricslab.html.twig",
}
assert changed==expected,(sorted(changed),sorted(expected))

for forbidden in (
 "analysis/chord_timeline_analysis.py",
 "public/assets/js/stems-mixer.js",
 "worker_app/ezscore_analysis_worker.pyw",
 "worker_app/server_control.py",
):
    assert forbidden not in changed

print("R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE_CONTRACT_OK")
