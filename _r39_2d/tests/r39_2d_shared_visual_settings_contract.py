#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

chord = (ROOT/"templates/song/chordslab.html.twig").read_text(encoding="utf-8")
lyric = (ROOT/"templates/song/lyricslab.html.twig").read_text(encoding="utf-8")
partial = (ROOT/"templates/song/components/_live_visual_settings.html.twig").read_text(encoding="utf-8")
css = (ROOT/"public/assets/css/components/ezscore-live-visual-settings.css").read_text(encoding="utf-8")
js = (ROOT/"public/assets/js/components/ezscore-live-visual-settings.js").read_text(encoding="utf-8")

assert "_live_visual_settings.html.twig" in chord
assert "_live_visual_settings.html.twig" in lyric
assert "context:'chords'" in chord
assert "context:'lyrics'" in lyric

for needle in (
    "data-chordslab-capo",
    "data-chordslab-timesig",
    "data-chordslab-profile",
    "data-chordslab-diagram",
    "data-chord-settings-form",
):
    assert needle in partial

assert "grid-template-areas:" in css
assert '"capo signature profile toggle"' in css
assert "@media(max-width:900px)" in css
assert "@media(max-width:640px)" in css
assert "@media(max-width:420px)" in css

assert "ezscore:visual:guitar-diagram" in js
assert "if (onLyricsLab)" in js
assert "if (onChordsLab)" in js
assert "location.reload();" in js

# Critical: no timeline/player JS files modified by this package.
assert "ezscore-live-visual-settings.js?v=20260930r39_2d" in chord
assert "ezscore-live-visual-settings.js?v=20260930r39_2d" in lyric
assert "ezscore-live-visual-settings.css?v=20260930r39_2d" in chord
assert "ezscore-live-visual-settings.css?v=20260930r39_2d" in lyric

print("R39_2D_SHARED_VISUAL_SETTINGS_CONTRACT_OK")
