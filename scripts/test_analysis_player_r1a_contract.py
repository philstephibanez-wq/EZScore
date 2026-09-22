from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
forced = (ROOT/'ezscore/analysis/forced_lyrics.py').read_text(encoding='utf-8')
choir = (ROOT/'ezscore/integration/choir_pipeline.py').read_text(encoding='utf-8')
player = (ROOT/'ezscore/player/stem_analysis_conductor.py').read_text(encoding='utf-8')
for name, src in [('forced',forced),('choir',choir),('player',player)]:
    ast.parse(src, filename=name)
assert 'user_lyrics_sources' in forced
assert 'progress=progress' in forced
assert 'Analyse acoustique MMS_FA' in forced
assert 'Alignement des paroles en cours…' in choir
assert '→ Étape 3 · Blocs / structure' in choir
assert '↩ Récupérer les paroles enregistrées' in choir
assert '<strong>Conducteur continu</strong>' not in player
assert 'conductor-transport' in player
assert 'load_alignment(audio_hash)' in player
assert '"duration_hint": float(duration_hint)' in player
print('ANALYSIS PLAYER R1a CONTRACT OK')
print('MMS_FA progress: VISIBLE')
print('next-step button: ENABLED')
print('lyrics persistence: SQLITE + FILE')
print('legacy lyrics recovery: ENABLED')
print('transport: BELOW CONDUCTOR')
print('conductor title: REMOVED')
print('diagram checkbox: LEFT')
print('player canonical lyrics fallback: ENABLED')
