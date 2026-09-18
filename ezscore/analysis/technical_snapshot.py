from __future__ import annotations

"""Read persisted technical truth produced by Analyse.

This module contains no analysis engine and performs no mutation.
It is the single read model consumed by presentation components such as
the STEM player.

Source priority:
1. canonical structure_analysis.json / beat_timeline;
2. canonical Whisper payload supplied by Analyse;
3. optional explicit backing_vocals_analysis.json.

Legacy karaoke-conductor caches are intentionally ignored: they are derived
player artifacts, not the technical source of truth.
"""

from pathlib import Path
import json
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def meter_default(work_dir: Path) -> dict[str, Any]:
    structure = _read_json(Path(work_dir) / "structure_analysis.json") or {}
    meter = dict(structure.get("meter", {}) or {})
    return {
        "signature": str(
            meter.get("signature")
            or structure.get("signature")
            or "4/4"
        ),
        "grouping": str(meter.get("grouping", "") or ""),
    }


def beats(work_dir: Path) -> list[dict[str, Any]]:
    """Project canonical beat_timeline to the player schema without analysis."""
    structure = _read_json(Path(work_dir) / "structure_analysis.json") or {}
    source = list(structure.get("beat_timeline", []) or [])
    if not source:
        return []

    tempo = float(structure.get("tempo", 120.0) or 120.0)
    default_interval = 60.0 / max(1.0, tempo)

    staged: list[tuple[float, dict[str, Any]]] = []
    for item in source:
        if not isinstance(item, dict):
            continue
        raw_time = item.get("time")
        if raw_time is None:
            raw_time = item.get("start")
        try:
            start = float(raw_time)
        except (TypeError, ValueError):
            continue
        if start < 0:
            continue
        staged.append((start, item))

    staged.sort(key=lambda row: row[0])
    if not staged:
        return []

    result: list[dict[str, Any]] = []
    for index, (start, item) in enumerate(staged):
        end = (
            staged[index + 1][0]
            if index + 1 < len(staged)
            else start + default_interval
        )

        chord = str(item.get("chord", ".") or ".").strip() or "."
        if chord.upper() in {"N", "NC", "N.C.", "NO_CHORD"}:
            chord = "."

        result.append(
            {
                "index": index,
                "start": round(start, 6),
                "end": round(float(end), 6),
                "chord": chord,
                "raw_chord": str(
                    item.get("chord_raw")
                    or item.get("raw_chord")
                    or ""
                ),
                "overlap": float(
                    item.get("chord_overlap")
                    or item.get("overlap")
                    or 0.0
                ),
            }
        )

    return result


def explicit_backing_words(work_dir: Path) -> list[dict[str, Any]]:
    """Return only backing vocals produced by a dedicated technical detector."""
    payload = _read_json(Path(work_dir) / "backing_vocals_analysis.json") or {}
    return list(payload.get("words", []) or [])


def status(work_dir: Path) -> dict[str, Any]:
    """Expose deterministic persisted-analysis readiness."""
    work_dir = Path(work_dir)
    speech = _read_json(work_dir / "whisper_original_small.json") or {}
    structure = _read_json(work_dir / "structure_analysis.json") or {}

    words = list(speech.get("words", []) or [])
    timeline = list(structure.get("beat_timeline", []) or [])
    chord_count = sum(
        1
        for item in timeline
        if str((item or {}).get("chord", ".") or ".").strip()
        not in {"", ".", "N", "NC", "N.C."}
    )

    return {
        "lyrics_ready": bool(words),
        "word_count": len(words),
        "structure_ready": bool(timeline),
        "beat_count": len(timeline),
        "chord_count": chord_count,
    }
