from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore" / "integration" / "choir_pipeline.py"


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    ast.parse(src, filename=str(TARGET))

    assert "LEAD_ONLY_LYRICS = True" in src

    forbidden = [
        "analyze_choirs",
        "align_choir_timeline",
        "choir_analysis_is_current",
        "timeline_alignment_is_current",
        "load_choir_analysis",
    ]
    for token in forbidden:
        assert token not in src, token

    purge_block = src[
        src.index("def _purge_legacy_choir_text_cache"):
        src.index("def install(")
    ]
    assert '(work / "lead_vocals.wav")' not in purge_block
    assert '(work / "backing_vocals.wav")' not in purge_block

    required = [
        'payload["backing_words"] = []',
        'payload["backing_word_count"] = 0',
        "def no_choir_words(",
        "base._derive_choir_words_from_vocals = no_choir_words",
        "base._supplement_only_words = no_supplement_words",
        "base._ensure_vocal_whisper_supplement = lead_words_passthrough",
        "return r12c._COMPONENT_R12C(",
        "speech_cache_is_current",
        "Analyse canonique du Chant",
    ]
    for token in required:
        assert token in src, token

    print("LEAD-ONLY LYRICS CONTRACT OK")
    print("lead lyrics: ENABLED")
    print("choir lyrics/transcription: DISABLED")
    print("lead/backing audio stems: PRESERVED")
    print("canonical timeline/cache guard: PRESERVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
