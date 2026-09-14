"""Phoneme timeline diagnostics for EZScore.

The current implementation deliberately separates two concepts:

- phonetic representation: derived from Whisper words;
- acoustic phoneme detection: future source, not claimed here.

The diagnostic timeline projects the derived phonetic units onto the
canonical audio/beat clock without depending on structural blocks.
"""

from __future__ import annotations

from bisect import bisect_right
import unicodedata

from ezscore.transcription import construire_timeline_phonetique


SOURCE_WHISPER_DERIVED = "whisper-derived"


def _split_phonetic_units(value: str) -> list[str]:
    """Split simplified IPA text into displayable phonetic units.

    Combining marks (notably the nasal tilde) stay attached to their base
    symbol.  A liaison marker is attached to the following consonant.
    """
    text = str(value or "").strip()
    units: list[str] = []
    pending_liaison = ""

    for char in text:
        if char.isspace() or char in {"'", "’", "-"}:
            continue

        if char == "‿":
            pending_liaison = "‿"
            continue

        if unicodedata.combining(char):
            if units:
                units[-1] += char
            continue

        unit = pending_liaison + char
        pending_liaison = ""
        units.append(unit)

    if pending_liaison:
        units.append(pending_liaison)

    return units


def _beat_position(
    time_value: float,
    beats,
    beats_per_measure: int,
) -> dict:
    source = list(beats or [])
    bpm = max(1, int(beats_per_measure or 4))

    if not source:
        return {
            "beat_index": None,
            "measure": None,
            "beat": None,
            "beat_start": None,
            "beat_end": None,
        }

    starts = [
        float(item.get("temps", 0.0) or 0.0)
        for item in source
    ]
    index = bisect_right(starts, float(time_value)) - 1

    if index < 0:
        return {
            "beat_index": None,
            "measure": 0,
            "beat": 0,
            "beat_start": None,
            "beat_end": starts[0],
        }

    index = min(index, len(source) - 1)
    item = source[index]
    start = float(item.get("temps", 0.0) or 0.0)
    end = float(
        item.get(
            "fin",
            source[index + 1].get("temps", start)
            if index + 1 < len(source)
            else start,
        )
        or start
    )

    return {
        "beat_index": index,
        "measure": (index // bpm) + 1,
        "beat": (index % bpm) + 1,
        "beat_start": start,
        "beat_end": end,
    }


def build_phoneme_timeline(
    resultat,
    beats,
    beats_per_measure: int,
) -> list[dict]:
    """Build a block-independent phoneme diagnostic timeline.

    Timing is currently inherited from Whisper word timestamps.  Phonetic
    units are distributed monotonically inside each word interval.  This is
    intentionally marked as derived rather than acoustic detection.
    """
    word_timeline = construire_timeline_phonetique(resultat)
    events: list[dict] = []

    for word_index, item in enumerate(word_timeline):
        word = str(item.get("Mot", "") or "").strip()
        phonetic = str(item.get("Phonétique", "") or "").strip()
        units = _split_phonetic_units(phonetic)

        start = float(item.get("Début", 0.0) or 0.0)
        end = max(
            start,
            float(item.get("Fin", start) or start),
        )

        if not units:
            continue

        duration = max(0.001, end - start)
        step = duration / len(units)

        for unit_index, phoneme in enumerate(units):
            p0 = start + unit_index * step
            p1 = end if unit_index == len(units) - 1 else start + (unit_index + 1) * step
            midpoint = (p0 + p1) / 2.0
            beat = _beat_position(
                midpoint,
                beats,
                beats_per_measure,
            )

            events.append({
                "phoneme": phoneme,
                "start": float(p0),
                "end": float(p1),
                "duration": float(max(0.0, p1 - p0)),
                "word": word,
                "word_index": int(word_index),
                "phoneme_index": int(unit_index),
                "measure": beat["measure"],
                "beat": beat["beat"],
                "beat_index": beat["beat_index"],
                "source": SOURCE_WHISPER_DERIVED,
                "acoustic": False,
                "liaison": phoneme.startswith("‿"),
            })

    return events


def diagnostic_rows(events) -> list[dict]:
    """Convert phoneme events to compact user-facing rows."""
    rows = []
    for event in events or []:
        measure = event.get("measure")
        beat = event.get("beat")
        rows.append({
            "Début": f'{float(event.get("start", 0.0)):.3f}',
            "Fin": f'{float(event.get("end", 0.0)):.3f}',
            "Durée ms": int(round(1000.0 * float(event.get("duration", 0.0)))),
            "Mesure": "—" if measure is None else int(measure),
            "Beat": "—" if beat is None else int(beat),
            "Phonème": str(event.get("phoneme", "") or ""),
            "Mot": str(event.get("word", "") or ""),
            "Source": (
                "Whisper → phonétique"
                if event.get("source") == SOURCE_WHISPER_DERIVED
                else str(event.get("source", "") or "")
            ),
        })
    return rows


def beat_phoneme_groups(events) -> list[dict]:
    """Compact beat-oriented view useful for musical diagnostics."""
    groups: list[dict] = []
    current_key = None
    current = None

    for event in events or []:
        key = (
            event.get("measure"),
            event.get("beat"),
        )
        if key != current_key:
            current_key = key
            current = {
                "measure": event.get("measure"),
                "beat": event.get("beat"),
                "start": float(event.get("start", 0.0)),
                "end": float(event.get("end", 0.0)),
                "phonemes": [],
                "words": [],
            }
            groups.append(current)

        current["end"] = float(event.get("end", current["end"]))
        phoneme = str(event.get("phoneme", "") or "")
        if phoneme:
            current["phonemes"].append(phoneme)
        word = str(event.get("word", "") or "")
        if word and (not current["words"] or current["words"][-1] != word):
            current["words"].append(word)

    return [
        {
            "Mesure": "—" if item["measure"] is None else int(item["measure"]),
            "Beat": "—" if item["beat"] is None else int(item["beat"]),
            "Temps": f'{item["start"]:.2f}–{item["end"]:.2f}s',
            "Phonèmes": " ".join(item["phonemes"]),
            "Paroles": " ".join(item["words"]),
        }
        for item in groups
    ]
