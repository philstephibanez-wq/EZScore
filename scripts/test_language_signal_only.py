from __future__ import annotations

"""Structural regression test for EZScore's audio-only language contract."""

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "ezscore" / "analysis" / "whisper_policy.py"
PIPELINE_PATH = REPO_ROOT / "ezscore" / "integration" / "language_pipeline.py"


FORBIDDEN_RUNTIME_NAMES = {
    "original_filename",
    "filename",
    "song_title",
    "title",
    "artist",
    "id3",
    "metadata",
    "tags",
}


def _runtime_identifiers(path: Path) -> set[str]:
    """Return executable identifiers, excluding comments and docstrings."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
        elif isinstance(node, ast.arg):
            names.add(node.arg.lower())

    return names


def _find_transcribe_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls: list[ast.Call] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "transcribe":
            calls.append(node)

    return calls


def _assert_no_metadata_language_inputs() -> None:
    runtime_names = (
        _runtime_identifiers(POLICY_PATH)
        | _runtime_identifiers(PIPELINE_PATH)
    )

    forbidden_found = sorted(
        name for name in FORBIDDEN_RUNTIME_NAMES
        if name in runtime_names
    )
    if forbidden_found:
        raise AssertionError(
            "Forbidden runtime metadata identifier(s) in language pipeline: "
            + ", ".join(forbidden_found)
        )

    pipeline_source = PIPELINE_PATH.read_text(encoding="utf-8")
    policy_source = POLICY_PATH.read_text(encoding="utf-8")

    if '"source": "audio_signal_only"' not in policy_source:
        raise AssertionError("Audio-only provenance marker missing.")

    if "LANGUAGE_POLICY_VERSION" not in pipeline_source:
        raise AssertionError("Versioned language-cache contract missing.")

    calls = _find_transcribe_calls(PIPELINE_PATH)
    if not calls:
        raise AssertionError("No Whisper transcribe() call found.")

    # Canonical STEM transcription must feed a PCM variable, never `source`
    # or another filesystem path.
    pcm_call_found = False
    for call in calls:
        if not call.args:
            continue
        first = call.args[0]
        if isinstance(first, ast.Name):
            arg_name = first.id
            if arg_name == "original_samples":
                pcm_call_found = True
            if arg_name in {"source", "path", "filename", "audio_filename"}:
                raise AssertionError(
                    "Whisper transcription receives a path/name instead of PCM: "
                    + arg_name
                )

    if not pcm_call_found:
        raise AssertionError(
            "Canonical transcription must pass `original_samples` to Whisper."
        )


def main() -> int:
    _assert_no_metadata_language_inputs()

    print("LANGUAGE AUDIO-ONLY CONTRACT OK")
    print("filename/title/artist/tags: not runtime language inputs")
    print("Whisper transcription input: PCM samples")
    print("legacy speech cache: invalidated by policy version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
