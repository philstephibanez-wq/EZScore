"""Canonical audio-time timelines for EZScore.

The three timelines share one timebase: seconds from the beginning of the
original audio file.

They are intentionally independent from visual blocks. Moving a block boundary
must never change an item's start/end timestamps.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


TIMELINE_SCHEMA_VERSION = 1
TIMEBASE = "audio_seconds"


def _stable_id(prefix: str, index: int, start: float, end: float, value: str) -> str:
    payload = f"{prefix}|{index}|{start:.6f}|{end:.6f}|{value}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def build_chord_timeline(musique: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a beat-accurate chord timeline.

    No block information is used. These events are the source of truth for
    later MIDI rendering and chord editing.
    """
    beats = list(musique.get("beats", []) or [])
    beats_per_measure = max(1, int(musique.get("beats_par_mesure", 4) or 4))
    result = []

    for pos, beat in enumerate(beats):
        start = float(beat.get("temps", 0.0) or 0.0)
        end = float(beat.get("fin", start) or start)
        if end < start:
            end = start

        beat_index = int(beat.get("index", pos) or pos)
        chord = str(beat.get("accord", ".") or ".")
        measure_no = beat_index // beats_per_measure + 1
        beat_in_measure = beat_index % beats_per_measure + 1

        result.append({
            "id": _stable_id("chord", beat_index, start, end, chord),
            "start": start,
            "end": end,
            "chord": chord,
            "beat_index": beat_index,
            "measure": measure_no,
            "beat": beat_in_measure,
            "confidence": float(beat.get("confiance", 0.0) or 0.0),
            "source": "analysis",
        })

    return result


def build_lyrics_timeline(resultat: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the canonical word timeline from Whisper timestamps."""
    result = []
    word_index = 0

    for segment_index, segment in enumerate(resultat.get("segments", []) or []):
        for word in segment.get("words", []) or []:
            text = str(word.get("word", "") or "").strip()
            if not text:
                continue

            start = float(word.get("start", 0.0) or 0.0)
            end = float(word.get("end", start) or start)
            if end < start:
                end = start

            result.append({
                "id": _stable_id("word", word_index, start, end, text),
                "start": start,
                "end": end,
                "text": text,
                "word_index": word_index,
                "segment_index": segment_index,
                "source": "whisper",
            })
            word_index += 1

    return result


def _fr_phonetic_word(word: str) -> str:
    """Same deliberately simple French phonetic approximation as R30.

    This is NOT acoustic phoneme recognition. It remains explicitly marked as
    whisper-derived until an acoustic phoneme model replaces it.
    """
    w = str(word or "").lower().strip()
    w = re.sub(r"[^a-zàâäéèêëîïôöùûüÿçœæ'-]", "", w)
    if not w:
        return ""

    replacements = [
        ("eaux", "o"), ("eau", "o"), ("aux", "o"), ("au", "o"),
        ("oin", "wɛ̃"), ("ain", "ɛ̃"), ("ein", "ɛ̃"), ("aim", "ɛ̃"),
        ("in", "ɛ̃"), ("im", "ɛ̃"), ("un", "œ̃"), ("um", "œ̃"),
        ("an", "ɑ̃"), ("am", "ɑ̃"), ("en", "ɑ̃"), ("em", "ɑ̃"),
        ("on", "ɔ̃"), ("om", "ɔ̃"), ("ou", "u"), ("oi", "wa"),
        ("gn", "ɲ"), ("ill", "j"), ("ph", "f"), ("ch", "ʃ"),
        ("th", "t"), ("qu", "k"), ("gu", "g"),
    ]
    for src, dst in replacements:
        w = w.replace(src, dst)

    w = re.sub(r"c(?=[eéièêëiy])", "s", w)
    w = w.replace("c", "k")
    w = re.sub(r"g(?=[eéièêëiy])", "ʒ", w)
    w = w.replace("j", "ʒ")
    w = w.replace("r", "ʁ")
    w = w.replace("u", "y")
    w = w.replace("é", "e")
    w = w.replace("er", "e")
    w = w.replace("ez", "e")
    w = w.replace("è", "ɛ")
    w = w.replace("ê", "ɛ")
    w = w.replace("ai", "ɛ")
    w = w.replace("ais", "ɛ")
    w = w.replace("ait", "ɛ")
    w = w.replace("ç", "s")
    w = w.replace("y", "j")
    w = w.replace("â", "ɑ")
    w = w.replace("ô", "o")
    w = re.sub(r"[tdspx]$", "", w)
    w = re.sub(r"e$", "", w)
    return w


_PHONEME_MULTI = (
    "wɛ̃", "ɛ̃", "œ̃", "ɑ̃", "ɔ̃",
)


def _split_phonetic_units(value: str) -> list[str]:
    """Split the simplified IPA string without breaking nasal units."""
    units = []
    i = 0
    value = str(value or "")

    while i < len(value):
        matched = None
        for unit in _PHONEME_MULTI:
            if value.startswith(unit, i):
                matched = unit
                break
        if matched:
            units.append(matched)
            i += len(matched)
            continue

        ch = value[i]
        if ch not in (" ", "-", "'", "‿"):
            units.append(ch)
        i += 1

    return units


def build_phoneme_timeline(
    resultat: dict[str, Any],
    lyrics_timeline: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build a phoneme timeline aligned inside each Whisper word.

    Timing is interpolated inside each word timestamp. Therefore every item is
    explicitly tagged `acoustic=False` and `source=whisper-derived`.
    """
    words = lyrics_timeline if lyrics_timeline is not None else build_lyrics_timeline(resultat)
    language = str(resultat.get("language", "") or "").lower()

    if language and not language.startswith("fr"):
        return []

    result = []
    phoneme_index = 0

    for word in words:
        text = str(word.get("text", "") or "")
        phonetic = _fr_phonetic_word(text)
        units = _split_phonetic_units(phonetic)
        if not units:
            continue

        w0 = float(word["start"])
        w1 = float(word["end"])
        duration = max(0.0, w1 - w0)
        step = duration / len(units) if units else 0.0

        for local_index, unit in enumerate(units):
            start = w0 + local_index * step
            end = w1 if local_index == len(units) - 1 else w0 + (local_index + 1) * step

            result.append({
                "id": _stable_id("phoneme", phoneme_index, start, end, unit),
                "start": start,
                "end": end,
                "phoneme": unit,
                "phoneme_index": phoneme_index,
                "word_id": word["id"],
                "word": text,
                "source": "whisper-derived",
                "acoustic": False,
            })
            phoneme_index += 1

    return result


def build_primary_timelines(
    musique: dict[str, Any],
    resultat: dict[str, Any],
) -> dict[str, Any]:
    """Build the 3 synchronized primary timelines."""
    lyrics = build_lyrics_timeline(resultat)
    return {
        "schema_version": TIMELINE_SCHEMA_VERSION,
        "timebase": TIMEBASE,
        "chords": build_chord_timeline(musique),
        "phonemes": build_phoneme_timeline(resultat, lyrics),
        "lyrics": lyrics,
    }


def active_at(timeline: list[dict[str, Any]], time_seconds: float) -> list[dict[str, Any]]:
    """Return every timeline item active at a given audio timestamp."""
    t = float(time_seconds)
    return [
        item
        for item in timeline
        if float(item.get("start", 0.0)) <= t < float(item.get("end", 0.0))
    ]
