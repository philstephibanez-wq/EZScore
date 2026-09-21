from __future__ import annotations

"""Canonical technical beat/chord timeline independent from block segmentation.

This cache is produced as soon as STEM + user lyrics are available and is the
single technical source for:
- STEM conductor,
- Paroles + accords editor,
- later block/structure segmentation.

It contains no visual blocks and no editorial decisions.
"""

import json
from pathlib import Path
from typing import Any

from ezscore.analysis.chords_quality import (
    analyze_chords_absolute,
    chord_for_interval,
)
from ezscore.analysis.rhythm_quality import analyze_beats as analyze_quality_beats


SCHEMA_VERSION = 1
FILENAME = "technical_timeline.json"
TIMEBASE = "original_audio_seconds"


def cache_path(work_dir: Path) -> Path:
    return Path(work_dir) / FILENAME


def _signature(path: Path) -> dict[str, int | str]:
    path = Path(path)
    stat = path.stat()
    return {
        "name": path.name,
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _valid(
    payload: dict[str, Any],
    *,
    source: Path,
    drums: Path,
) -> bool:
    return bool(
        int(payload.get("schema_version", 0) or 0) == SCHEMA_VERSION
        and str(payload.get("timebase", "") or "") == TIMEBASE
        and len(list(payload.get("beat_timeline", []) or [])) >= 2
        and dict(payload.get("source_signature", {}) or {}) == _signature(source)
        and dict(payload.get("drums_signature", {}) or {}) == _signature(drums)
    )


def load(
    work_dir: Path,
    *,
    source: Path | None = None,
    drums: Path | None = None,
) -> dict[str, Any] | None:
    path = cache_path(work_dir)
    if not path.is_file():
        return None

    try:
        payload = dict(json.loads(path.read_text(encoding="utf-8")) or {})
    except Exception:
        return None

    if source is not None and drums is not None:
        try:
            if not _valid(payload, source=Path(source), drums=Path(drums)):
                return None
        except OSError:
            return None
    else:
        if not (
            int(payload.get("schema_version", 0) or 0) == SCHEMA_VERSION
            and str(payload.get("timebase", "") or "") == TIMEBASE
            and len(list(payload.get("beat_timeline", []) or [])) >= 2
        ):
            return None

    return payload


def _write(work_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = cache_path(work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)
    return payload


def import_from_structure(
    work_dir: Path,
    *,
    structure: dict[str, Any],
    source: Path,
    drums: Path,
) -> dict[str, Any] | None:
    """Promote an existing canonical structure beat timeline without reanalysis."""
    beats = list(structure.get("beat_timeline", []) or [])
    if len(beats) < 2:
        return None

    payload = {
        "schema_version": SCHEMA_VERSION,
        "timebase": TIMEBASE,
        "source": "existing_structure_analysis",
        "tempo": float(structure.get("tempo", 0.0) or 0.0),
        "beat_count": len(beats),
        "beat_timeline": beats,
        "source_signature": _signature(source),
        "drums_signature": _signature(drums),
        "analysis_engines": dict(structure.get("analysis_engines", {}) or {}),
    }
    return _write(work_dir, payload)


def ensure(
    *,
    work_dir: Path,
    source: Path,
    drums: Path,
    chord_cache_path: Path,
    existing_structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return or build the canonical beat/chord timeline.

    Harmony comes from original audio.
    Rhythm comes from the drums STEM.
    No meter and no block segmentation is applied here.
    """
    work_dir = Path(work_dir)
    source = Path(source)
    drums = Path(drums)

    current = load(
        work_dir,
        source=source,
        drums=drums,
    )
    if current is not None:
        return current

    if existing_structure:
        promoted = import_from_structure(
            work_dir,
            structure=existing_structure,
            source=source,
            drums=drums,
        )
        if promoted is not None:
            return promoted

    rhythm = analyze_quality_beats(drums)
    beat_times = [float(x) for x in list(rhythm.get("beats", []) or [])]
    tempo = float(rhythm.get("tempo", 0.0) or 0.0)
    if len(beat_times) < 2:
        raise RuntimeError("Timeline rythmique insuffisante.")

    chord_payload = analyze_chords_absolute(
        source,
        cache_path=Path(chord_cache_path),
        force=False,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError("Timeline harmonique lv-chordia vide.")

    beat_timeline: list[dict[str, Any]] = []
    for index, start in enumerate(beat_times):
        end = (
            beat_times[index + 1]
            if index + 1 < len(beat_times)
            else start + 60.0 / max(1.0, tempo)
        )
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments,
            start,
            end,
        )
        beat_timeline.append(
            {
                "index": int(index),
                "time": round(float(start), 6),
                "strength": 0.0,
                "chord": str(chord),
                "chord_raw": str(raw_chord),
                "chord_overlap": round(float(overlap), 6),
                "rhythm_engine": str(rhythm.get("engine", "") or ""),
                "harmony_engine": str(chord_payload.get("engine", "") or ""),
            }
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "timebase": TIMEBASE,
        "source": "technical_analysis",
        "tempo": tempo,
        "beat_count": len(beat_timeline),
        "beat_timeline": beat_timeline,
        "source_signature": _signature(source),
        "drums_signature": _signature(drums),
        "analysis_engines": {
            "rhythm": str(rhythm.get("engine", "") or ""),
            "harmony": str(chord_payload.get("engine", "") or ""),
            "harmony_dictionary": str(chord_payload.get("dictionary", "") or ""),
        },
    }
    return _write(work_dir, payload)


def invalidate(work_dir: Path) -> None:
    try:
        cache_path(work_dir).unlink()
    except FileNotFoundError:
        pass
