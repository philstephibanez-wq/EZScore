from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

forced = (ROOT / "ezscore/analysis/forced_lyrics.py").read_text(encoding="utf-8")
integration = (ROOT / "ezscore/integration/choir_pipeline.py").read_text(encoding="utf-8")
layout = (ROOT / "ezscore/player/lyrics_layout.py").read_text(encoding="utf-8")

for name, src in (
    ("forced_lyrics.py", forced),
    ("choir_pipeline.py", integration),
    ("lyrics_layout.py", layout),
):
    ast.parse(src, filename=name)

for token in (
    'ENGINE = "torchaudio-mms-fa"',
    '"source": "user_text+lead_vocals"',
    '"language_detection": "none"',
    '"transcription": "none"',
    '"acoustic_source": "lead_vocals.wav"',
    "bundle = torchaudio.pipelines.MMS_FA",
    "token_spans = aligner(emission, tokenized)",
):
    assert token in forced, token

assert "install_language_pipeline" not in integration
assert "detect_language_profile" not in integration
assert "model.transcribe" not in integration
assert "model.transcribe" not in forced

assert 'payload["backing_words"] = []' in integration
assert 'payload["backing_word_count"] = 0' in integration
assert "whisper_backing_small.json" in integration

assert "Texte exact du chant" in integration
assert "ezstem_speech_" in integration
assert "Aligner le texte sur le Chant" in integration

assert "ezLayoutLaneNodes({" in layout
assert "ezVisualXForTime(" in layout
assert "leadVisualXs" in layout
assert "minGap:12" in layout

print("MANUAL LYRICS / FORCED ALIGNMENT CONTRACT OK")
print("free transcription: DISABLED")
print("audio language detection: DISABLED")
print("lyrics source: USER TEXT")
print("acoustic source: lead_vocals.wav")
print("forced alignment: MMS_FA")
print("choir lyrics: DISABLED")
print("word collision layout: ENABLED")
