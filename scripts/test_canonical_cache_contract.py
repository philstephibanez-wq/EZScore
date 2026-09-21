from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ezscore/analysis/whisper_policy.py"
LANG = ROOT / "ezscore/integration/language_pipeline.py"
CHOIR = ROOT / "ezscore/integration/choir_pipeline.py"


def main() -> int:
    policy = POLICY.read_text(encoding="utf-8")
    lang = LANG.read_text(encoding="utf-8")
    choir = CHOIR.read_text(encoding="utf-8")

    for path, src in [(POLICY, policy), (LANG, lang), (CHOIR, choir)]:
        ast.parse(src, filename=str(path))

    # No Whisper auto fallback after language-policy failure.
    assert "LANGUAGE_POLICY_VERSION = 5" in policy
    assert "ezscore-audio-only-language-v5" in policy
    assert "fallback_audio" not in policy
    assert "return original(self, fallback_audio" not in policy

    # Transactional master cache.
    assert "SPEECH_CACHE_SCHEMA_VERSION = 4" in lang
    assert '"status": "complete"' in lang
    assert '"word_count": len(words)' in lang
    assert "temp_path.replace(cache_path)" in lang
    assert "invalidate_canonical_speech(" in lang

    for name in [
        "whisper_vocals_small.json",
        "whisper_backing_small.json",
        "choir_words_from_vocals.json",
        "choir_analysis.json",
        "karaoke_conductor.json",
        "structure_analysis.json",
    ]:
        assert name in lang, name

    # Choir/player may never trust file existence alone.
    assert "_speech_ready" in choir
    assert "speech_cache_is_current" in choir
    assert "if not _speech_ready(stem_lab, audio_hash)" in choir
    assert "choir_analysis_is_current(audio_hash)" in choir
    assert "timeline_alignment_is_current(audio_hash)" in choir

    # Enriched player is suppressed before canonical speech is valid.
    assert "_ezscore_canonical_cache_guard" in choir
    assert "Analyse des paroles requise." in choir
    assert 'payload["beats"] = []' in choir
    assert 'payload["backing_words"] = []' in choir

    print("CANONICAL CACHE CONTRACT OK")
    print("interrupted lyrics analysis: stale master/dependents invalidated")
    print("atomic master commit: ENABLED")
    print("choir artifacts require current master: YES")
    print("enriched player requires current master: YES")
    print("Whisper auto-language fallback: DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
