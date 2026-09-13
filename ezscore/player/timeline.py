"""Canonical player timelines built from EZScore's effective beat grid."""

from __future__ import annotations


def _beat_end(source_beats, index: int) -> float:
    beat = source_beats[index]
    start = max(0.0, float(beat.get("temps", 0.0) or 0.0))
    if index + 1 < len(source_beats):
        return max(
            start + 0.02,
            float(source_beats[index + 1].get("temps", start + 0.5) or start + 0.5),
        )
    interval = max(0.08, float(beat.get("intervalle", 0.5) or 0.5))
    return start + interval


def build_player_timeline(
    *,
    beats,
    lyrics_words=None,
    beats_per_measure: int = 4,
    chord_diagrams=None,
):
    """Build the canonical one-item-per-beat timeline."""
    source_beats = list(beats or [])
    words = list(lyrics_words or [])
    diagrams = dict(chord_diagrams or {})
    bpm = max(1, int(beats_per_measure or 4))
    items = []
    current_chord = ""

    for index, beat in enumerate(source_beats):
        start = max(0.0, float(beat.get("temps", 0.0) or 0.0))
        end = _beat_end(source_beats, index)
        raw = str(beat.get("accord", "") or "").strip()
        chord_change = False

        if raw == ".":
            current_chord = ""
        elif raw == "-":
            pass
        elif raw:
            current_chord = raw
            chord_change = True

        lyric = " ".join(
            str(word.get("text", "") or "").strip()
            for word in words
            if start <= float(word.get("start", 0.0) or 0.0) < end
        ).strip()

        items.append({
            "time": start,
            "end": end,
            "beat": (index % bpm) + 1,
            "measure": (index // bpm) + 1,
            "chord": current_chord,
            "raw_chord": raw,
            "chord_change": bool(chord_change),
            "lyric": lyric,
            "diagram": diagrams.get(current_chord, ""),
        })

    return items


def build_measure_timeline(
    *,
    beats,
    lyrics_words=None,
    beats_per_measure: int = 4,
    chord_diagrams=None,
):
    """Build one visual card per measure.

    The card follows the same compact semantics as the Grille: a main chord
    appears once, while the beat row shows '-' / '.' and any exceptional
    mid-measure chord change. Playback updates the current beat highlight
    inside the card instead of scrolling the ribbon on every beat.
    """
    beat_items = build_player_timeline(
        beats=beats,
        lyrics_words=lyrics_words,
        beats_per_measure=beats_per_measure,
        chord_diagrams=chord_diagrams,
    )
    bpm = max(1, int(beats_per_measure or 4))
    measures = []

    for first in range(0, len(beat_items), bpm):
        group = beat_items[first:first + bpm]
        if not group:
            continue

        start = float(group[0]["time"])
        end = float(group[-1]["end"])

        primary = ""
        for item in group:
            raw = str(item.get("raw_chord", "") or "")
            if raw not in ("", "-", "."):
                primary = raw
                break
        if not primary:
            primary = str(group[0].get("chord", "") or "")

        beat_tokens = []
        beat_times = []
        beat_chords = []
        beat_diagrams = []

        for item in group:
            raw = str(item.get("raw_chord", "") or "")
            effective = str(item.get("chord", "") or "")
            if raw not in ("", "-", "."):
                token = "-" if raw == primary else raw
            elif raw == ".":
                token = "."
            else:
                token = "-"

            beat_tokens.append(token)
            beat_times.append(float(item["time"]))
            beat_chords.append(effective)
            beat_diagrams.append(str(item.get("diagram", "") or ""))

        lyric = " ".join(
            str(item.get("lyric", "") or "").strip()
            for item in group
            if str(item.get("lyric", "") or "").strip()
        ).strip()

        measures.append({
            "measure": int(group[0]["measure"]),
            "time": start,
            "end": end,
            "primary_chord": primary,
            "beat_tokens": beat_tokens,
            "beat_times": beat_times,
            "beat_chords": beat_chords,
            "beat_diagrams": beat_diagrams,
            "lyric": lyric,
        })

    return measures
