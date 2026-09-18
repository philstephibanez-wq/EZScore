from __future__ import annotations

"""Read-only view of the technical truth produced by Analyse.

No engine is executed here.

Persisted sources:
- whisper_original_small.json
- structure_analysis.json
- chord_analysis_lv_chordia.json
- optional backing_vocals_analysis.json

If structure_analysis.json contains beat timestamps but old/empty chord fields,
the already persisted chord segments are projected onto those beats in memory.
That is a read-only projection, not a re-analysis.
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


def _valid_chord(value: Any) -> bool:
    chord = str(value or "").strip()
    return chord not in {"", ".", "N", "NC", "N.C.", "no_chord"}


def _segment_for_interval(
    segments: list[dict[str, Any]],
    start: float,
    end: float,
) -> tuple[str, str, float]:
    t0 = float(start)
    t1 = max(t0 + 1e-6, float(end))

    best = None
    best_overlap = 0.0

    for segment in segments:
        try:
            s0 = float(segment.get("start", 0.0) or 0.0)
            s1 = float(segment.get("end", s0) or s0)
        except (TypeError, ValueError):
            continue

        overlap = max(0.0, min(t1, s1) - max(t0, s0))
        if overlap > best_overlap:
            best_overlap = overlap
            best = segment

    if best is None:
        return ".", "", 0.0

    chord = str(best.get("chord", ".") or ".").strip() or "."
    if chord in {"N", "NC", "N.C.", "no_chord"}:
        chord = "."

    raw = str(best.get("raw_chord", best.get("chord", "")) or "")
    ratio = best_overlap / max(1e-6, t1 - t0)
    return chord, raw, max(0.0, min(1.0, float(ratio)))


def beats(work_dir: Path) -> list[dict[str, Any]]:
    """Project persisted Analyse artifacts to the player schema."""
    work_dir = Path(work_dir)
    structure = _read_json(work_dir / "structure_analysis.json") or {}
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
        if start >= 0:
            staged.append((start, item))

    staged.sort(key=lambda row: row[0])
    if not staged:
        return []

    chord_payload = _read_json(work_dir / "chord_analysis_lv_chordia.json") or {}
    chord_segments = [
        item for item in list(chord_payload.get("segments", []) or [])
        if isinstance(item, dict)
    ]

    result: list[dict[str, Any]] = []

    for index, (start, item) in enumerate(staged):
        end = (
            staged[index + 1][0]
            if index + 1 < len(staged)
            else start + default_interval
        )

        chord = str(item.get("chord", ".") or ".").strip() or "."
        raw_chord = str(
            item.get("chord_raw")
            or item.get("raw_chord")
            or ""
        )
        overlap = float(
            item.get("chord_overlap")
            or item.get("overlap")
            or 0.0
        )

        # Compatibility for earlier STEM_LAB structure files:
        # reuse persisted lv-chordia segments, never run lv-chordia here.
        if not _valid_chord(chord) and chord_segments:
            chord, raw_chord, overlap = _segment_for_interval(
                chord_segments,
                start,
                end,
            )

        if chord in {"", "N", "NC", "N.C.", "no_chord"}:
            chord = "."

        result.append(
            {
                "index": index,
                "start": round(start, 6),
                "end": round(float(end), 6),
                "chord": chord,
                "raw_chord": raw_chord,
                "overlap": overlap,
            }
        )

    return result


def explicit_backing_words(work_dir: Path) -> list[dict[str, Any]]:
    payload = _read_json(Path(work_dir) / "backing_vocals_analysis.json") or {}
    return list(payload.get("words", []) or [])


def status(work_dir: Path) -> dict[str, Any]:
    work_dir = Path(work_dir)
    speech = _read_json(work_dir / "whisper_original_small.json") or {}
    structure = _read_json(work_dir / "structure_analysis.json") or {}
    projected_beats = beats(work_dir)

    words = list(speech.get("words", []) or [])
    chord_count = sum(
        1
        for item in projected_beats
        if _valid_chord(item.get("chord"))
    )

    return {
        "lyrics_ready": bool(words),
        "word_count": len(words),
        "structure_ready": bool(
            list(structure.get("beat_timeline", []) or [])
        ),
        "beat_count": len(projected_beats),
        "chord_count": chord_count,
    }
