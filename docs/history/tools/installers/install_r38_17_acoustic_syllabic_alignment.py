#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
ANALYSIS=ROOT/"analysis/lyrics_timeline_analysis.py"
RESULT=ROOT/"src/Service/LyricsTimelineResultService.php"
JS=ROOT/"public/assets/js/lyricslab-r37.js"
TWIG=ROOT/"templates/song/lyricslab.html.twig"
PATCH_MARK="# R38.17 acoustic syllabic alignment correction"

PY_PATCH=r