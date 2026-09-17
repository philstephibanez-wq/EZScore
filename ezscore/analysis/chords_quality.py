"""High-quality, time-continuous chord recognition for EZScore analysis.

The MP3/original audio is the only temporal reference.
This module does not quantize chords to beats or measures.  It first produces
absolute-time chord segments, then callers may project those segments onto any
metric grid without moving the original timestamps.

Primary engine:
    lv-chordia (ISMIR 2019 large-vocabulary 5-network ensemble + HMM)

No silent fallback is provided.  If the engine is unavailable, analysis fails
explicitly so a lower-quality recognizer cannot silently replace it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ENGINE = "lv-chordia"
CHORD_DICTIONARY = "submission"
SCHEMA_VERSION = 1


def quality_chord_engine_available() -> bool:
    try:
        return importlib.util.find_spec("lv_chordia") is not None
    except Exception:
        return False


def _ezscore_label(raw: str) -> str:
    """Convert JAMS/Harte-like lv-chordia labels to EZScore display labels."""
    label = str(raw or "N").strip()
    if not label or label == "N":
        return "N"

    bass = ""
    if "/" in label:
        label, bass_part = label.split("/", 1)
        bass_part = bass_part.strip()
        if bass_part:
            bass = "/" + bass_part

    if ":" not in label:
        return label + bass

    root, quality = label.split(":", 1)
    root = root.strip()
    quality = quality.strip()

    quality_map = {
        "maj": "",
        "min": "m",
        "7": "7",
        "maj7": "maj7",
        "min7": "m7",
        "dim": "dim",
        "dim7": "dim7",
        "hdim7": "m7b5",
        "aug": "aug",
        "sus2": "sus2",
        "sus4": "sus4",
        "min6": "m6",
        "maj6": "6",
        "min9": "m9",
        "maj9": "maj9",
        "9": "9",
        "11": "11",
        "13": "13",
    }
    suffix = quality_map.get(quality, quality)
    return f"{root}{suffix}{bass}"


def analyze_chords_absolute(
    audio_path: Path,
    *,
    cache_path: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Run the neural ensemble on the original audio and persist raw segments."""
    audio_path = Path(audio_path)
    cache_path = Path(cache_path)

    if not audio_path.is_file():
        raise FileNotFoundError(str(audio_path))

    if not force and cache_path.is_file():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            int(payload.get("schema_version", 0) or 0) == SCHEMA_VERSION
            and str(payload.get("engine", "")) == ENGINE
            and str(payload.get("dictionary", "")) == CHORD_DICTIONARY
        ):
            return payload

    if not quality_chord_engine_available():
        raise RuntimeError(
            "Moteur d'accords haute qualité absent : installez `lv-chordia`. "
            "EZScore refuse de revenir silencieusement au classifieur chroma historique."
        )

    from lv_chordia.chord_recognition import chord_recognition

    raw_segments = chord_recognition(
        audio_path=str(audio_path),
        chord_dict_name=CHORD_DICTIONARY,
    )

    segments: list[dict[str, Any]] = []
    for item in raw_segments or []:
        start = float(item.get("start_time", 0.0) or 0.0)
        end = float(item.get("end_time", start) or start)
        raw = str(item.get("chord", "N") or "N").strip()
        if end <= start:
            continue
        segments.append(
            {
                "start": round(start, 6),
                "end": round(end, 6),
                "chord": _ezscore_label(raw),
                "raw_chord": raw,
            }
        )

    if not segments:
        raise RuntimeError("lv-chordia n'a retourné aucun segment harmonique exploitable.")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "engine": ENGINE,
        "dictionary": CHORD_DICTIONARY,
        "source": "original_audio",
        "timebase": "original_audio_seconds",
        "segment_count": len(segments),
        "segments": segments,
    }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(cache_path)
    return payload


def chord_for_interval(
    segments: list[dict[str, Any]],
    start: float,
    end: float,
) -> tuple[str, str, float]:
    """Return the chord with the largest overlap with [start, end)."""
    t0 = float(start)
    t1 = max(t0 + 1e-6, float(end))

    best = None
    best_overlap = 0.0
    for segment in segments or []:
        s0 = float(segment.get("start", 0.0) or 0.0)
        s1 = float(segment.get("end", s0) or s0)
        overlap = max(0.0, min(t1, s1) - max(t0, s0))
        if overlap > best_overlap:
            best_overlap = overlap
            best = segment

    if best is None:
        midpoint = (t0 + t1) * 0.5
        nearest = min(
            segments or [],
            key=lambda segment: abs(
                ((float(segment.get("start", 0.0)) + float(segment.get("end", 0.0))) * 0.5)
                - midpoint
            ),
            default=None,
        )
        if nearest is None:
            return "N", "N", 0.0
        best = nearest

    ratio = best_overlap / max(1e-6, t1 - t0)
    return (
        str(best.get("chord", "N") or "N"),
        str(best.get("raw_chord", best.get("chord", "N")) or "N"),
        float(max(0.0, min(1.0, ratio))),
    )
