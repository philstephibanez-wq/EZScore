"""MIDI event generation from EZScore's effective edited beat grid."""

from __future__ import annotations

import re

MIDI_INSTRUMENTS = {
    "Electric Guitar (clean)": 27,
    "Acoustic Grand Piano": 0,
}

_PC = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


def chord_symbol_to_midi_notes(symbol: str) -> list[int]:
    """Translate a practical guitar chord symbol to MIDI notes.

    The player intentionally voices compact chords in the middle register.
    It supports the common symbols produced or edited in EZScore, including
    major/minor, sevenths, diminished, augmented, suspended and slash bass.
    """
    raw = str(symbol or "").strip()
    if not raw or raw in {".", "-", "?", "^"}:
        return []

    main, slash, bass = raw.partition("/")
    match = re.match(r"^([A-G])([#b]?)(.*)$", main)
    if not match:
        return []

    root_name = match.group(1) + match.group(2)
    if root_name not in _PC:
        return []

    suffix = match.group(3).strip().lower()
    root = 48 + _PC[root_name]
    if root > 59:
        root -= 12

    if "dim7" in suffix or "°7" in suffix:
        intervals = [0, 3, 6, 9]
    elif "dim" in suffix or "°" in suffix:
        intervals = [0, 3, 6]
    elif "aug" in suffix or "+" in suffix:
        intervals = [0, 4, 8]
    elif "sus2" in suffix:
        intervals = [0, 2, 7]
    elif "sus" in suffix:
        intervals = [0, 5, 7]
    elif suffix.startswith("m") and not suffix.startswith("maj"):
        intervals = [0, 3, 7]
    else:
        intervals = [0, 4, 7]

    if "maj7" in suffix:
        intervals.append(11)
    elif "7" in suffix:
        intervals.append(10)
    if "6" in suffix and 9 not in intervals:
        intervals.append(9)
    if "add9" in suffix or suffix.endswith("9"):
        intervals.append(14)

    notes = sorted({root + interval for interval in intervals})

    if slash:
        bass_match = re.match(r"^([A-G])([#b]?)", bass.strip())
        if bass_match:
            bass_name = bass_match.group(1) + bass_match.group(2)
            if bass_name in _PC:
                bass_note = 36 + _PC[bass_name]
                if bass_note > 47:
                    bass_note -= 12
                notes = [bass_note] + notes

    return notes


def accent_velocity(beat_position: int, signature: str, beats_per_measure: int) -> int:
    """Return GM velocity with stronger metric accents."""
    pos = int(beat_position)
    signature = str(signature or "4/4")
    bpm = max(1, int(beats_per_measure or 4))

    patterns = {
        "2/4": [112, 84],
        "3/4": [112, 82, 82],
        "4/4": [114, 82, 98, 82],
        "6/8": [114, 76, 76, 98, 76, 76],
        "12/8": [114, 74, 74, 98, 74, 74, 104, 74, 74, 98, 74, 74],
    }
    pattern = patterns.get(signature)
    if pattern and len(pattern) == bpm:
        return int(pattern[pos % bpm])
    if pos == 0:
        return 114
    if bpm >= 4 and pos == bpm // 2:
        return 98
    return 82


def build_chord_midi_events(
    beats,
    signature: str = "4/4",
    beats_per_measure: int = 4,
    program: int = 27,
    gate_ratio: float = 0.48,
    strum_ms: float = 12.0,
):
    """Build the canonical MIDI event stream from the effective beat grid.

    This stream is the single source for both editor playback and .mid export.
    One downstroke is generated per beat; strong beats use higher velocity.
    """
    events = [{
        "time": 0.0,
        "status": 0xC0,
        "data1": int(program) & 0x7F,
        "data2": None,
        "kind": "program",
    }]

    beats_per_measure = max(1, int(beats_per_measure or 4))
    gate_ratio = min(0.90, max(0.12, float(gate_ratio or 0.48)))
    strum_seconds = max(0.0, float(strum_ms or 0.0)) / 1000.0
    current_chord = None

    for seq_index, beat in enumerate(beats):
        symbol = str(beat.get("accord", "") or "").strip()
        if symbol == ".":
            current_chord = None
            continue
        if symbol == "-":
            symbol = current_chord or ""
        elif symbol:
            current_chord = symbol

        notes = chord_symbol_to_midi_notes(symbol)
        if not notes:
            continue

        start = max(0.0, float(beat.get("temps", 0.0)))
        interval = max(
            0.08,
            float(
                beat.get(
                    "intervalle",
                    float(beat.get("fin", start)) - start,
                )
                or 0.5
            ),
        )
        beat_position = seq_index % beats_per_measure
        velocity = accent_velocity(beat_position, signature, beats_per_measure)

        note_starts = []
        for note_index, note in enumerate(notes):
            note_start = start + note_index * strum_seconds
            note_starts.append((int(note), note_start))
            events.append({
                "time": note_start,
                "status": 0x90,
                "data1": int(note),
                "data2": int(velocity),
                "kind": "note_on",
                "chord": symbol,
                "beat": int(seq_index),
                "velocity": int(velocity),
            })

        common_end = start + max(0.06, interval * gate_ratio)
        for note, note_start in note_starts:
            events.append({
                "time": max(note_start + 0.04, common_end),
                "status": 0x80,
                "data1": int(note),
                "data2": 0,
                "kind": "note_off",
                "chord": symbol,
                "beat": int(seq_index),
            })

    priority = {"program": 0, "note_off": 1, "note_on": 2}
    events.sort(key=lambda event: (
        float(event["time"]),
        priority.get(event["kind"], 9),
        int(event.get("data1", 0)),
    ))
    return events
