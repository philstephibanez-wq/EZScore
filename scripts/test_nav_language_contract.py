from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/views/navigation-breadcrumb.score"
RESPONSIVE = ROOT / "ezscore/ui/responsive.py"
POLICY = ROOT / "ezscore/analysis/whisper_policy.py"
PIPELINE = ROOT / "ezscore/integration/language_pipeline.py"


def main() -> int:
    template = TEMPLATE.read_text(encoding="utf-8")
    responsive = RESPONSIVE.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")

    assert "{{{ items_html }}}" in template
    assert not re.search(r"(?<!\{)\{\{\s*items_html\s*\}\}(?!\})", template)
    assert "_install_nav_markup_fix" not in responsive

    assert "LANGUAGE_POLICY_VERSION = 4" in policy
    assert "ezscore-audio-only-language-v4" in policy
    assert 'kwargs["language"] = primary' in policy
    assert "Langue vocale indéterminable" in policy

    assert "SPEECH_CACHE_SCHEMA_VERSION = 3" in pipeline
    assert 'transcribe_kwargs["language"] = primary_language' in pipeline
    assert "Transcription annulée avant Whisper" in pipeline

    forbidden_runtime_names = {
        "original_filename", "filename", "song_title", "title",
        "artist", "id3", "metadata", "tags",
    }
    for path, source in [(POLICY, policy), (PIPELINE, pipeline)]:
        tree = ast.parse(source, filename=str(path))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
        bad = forbidden_runtime_names & names
        assert not bad, f"metadata language input in {path.name}: {sorted(bad)}"

    print("NAV SCORE RAW HTML OK")
    print("LANGUAGE AUDIO-ONLY V4 OK")
    print("Whisper global auto fallback: DISABLED")
    print("speech cache schema: 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
