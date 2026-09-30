#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

twig = (ROOT/"templates/song/lyricslab.html.twig").read_text(encoding="utf-8")
js = (ROOT/"public/assets/js/lyricslab-timeline-r39.js").read_text(encoding="utf-8")
css = (ROOT/"public/assets/css/lyricslab-r37.css").read_text(encoding="utf-8")
catalog = (ROOT/"src/Controller/CatalogController.php").read_text(encoding="utf-8")
diag_js = (ROOT/"public/assets/js/components/ezscore-chord-diagram.js").read_text(encoding="utf-8")
diag_css = (ROOT/"public/assets/css/components/ezscore-chord-diagram.css").read_text(encoding="utf-8")

# Shared diagram assets are loaded in Lyrics.
assert "/assets/css/components/ezscore-chord-diagram.css?v=20260930r39_3" in twig
assert "/assets/js/components/ezscore-chord-diagram.js?v=20260930r39_3" in twig
assert "/assets/css/lyricslab-r37.css?v=20260930r39_5full" in twig
assert "/assets/js/lyricslab-timeline-r39.js?v=20260930r39_5full" in twig

# Correct placement: diagram is created INSIDE lyrics-ribbon-stage.
assert '<div class="lyrics-stage-diagram ez-chord-diagram" data-lyrics-stage-diagram hidden></div>' in js
assert "window.EZScoreChordDiagram?.render(diagram,label)" in js
assert "timeline.activeEventAt(chords,ms)" in js
assert "diagram.style.left=x+'px'" in js
assert "diagramToggle?.addEventListener('change',()=>renderAt(lastTime,true))" in js
assert "const SHAPES" not in js

# Same component and same base size as Chords.
assert "width:150px" in diag_css
assert "width:128px" in diag_css
assert "window.EZScoreChordDiagram" in diag_js

# Explicit recovered/reserved upper band.
assert "/* R39.5 FULL — shared Chords diagram lives inside the Lyrics ribbon stage." in css
assert "height:392px!important" in css
assert "top:6px!important" in css
assert "top:174px!important" in css
assert "top:284px!important" in css

# Catalog 500 regression fixed.
assert "$requestedStatus = SongStatus::tryFrom" in catalog
assert "?? $song->getStatus();" in catalog
assert "$this->applyStatus($song, $requestedStatus);" in catalog

print("R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX_CONTRACT_OK")
