#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
s = (ROOT/"templates/song/lyricslab.html.twig").read_text(encoding="utf-8")

include = (
    "{% include 'song/components/_live_visual_settings.html.twig' with {\n"
    "    song:song,\n"
    "    context:'lyrics'\n"
    "} %}"
)

assert s.count(include) == 1

timeline_anchor = '<section class="panel chordslab-prompter"\n         data-lyricslab'
idx_inc = s.index(include)
idx_timeline = s.index(timeline_anchor)
assert idx_inc < idx_timeline

source_panel = '<section class="panel chordslab-settings lyricslab-source-panel">'
idx_source = s.index(source_panel)
assert idx_source < idx_inc

print("R39_2F_MOVE_VISUAL_SETTINGS_LYRICS_CONTRACT_OK")
