"""Canonical player timeline built from EZScore's effective beat grid."""

from __future__ import annotations


def build_player_timeline(
    *,
    beats,
    lyrics_words=None,
    beats_per_measure: int = 4,
    chord_diagrams=None,
):
    """Build one visual player item per beat.

    The effective chord grid is authoritative. "-" carries the preceding chord,
    "." clears it. Lyrics are assigned to the beat interval containing their
    timestamp. The resulting structure is shared by View and Edition players.
    """
    source_beats = list(beats or [])
    words = list(lyrics_words or [])
    diagrams = dict(chord_diagrams or {})
    bpm = max(1, int(beats_per_measure or 4))
    items = []
    current_chord = ""

    for index, beat in enumerate(source_beats):
        start = max(0.0, float(beat.get("temps", 0.0) or 0.0))
        if index + 1 < len(source_beats):
            end = max(start + 0.02, float(source_beats[index + 1].get("temps", start + 0.5) or start + 0.5))
        else:
            interval = max(0.08, float(beat.get("intervalle", 0.5) or 0.5))
            end = start + interval

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
            "chord_change": bool(chord_change),
            "lyric": lyric,
            "diagram": diagrams.get(current_chord, ""),
        })

    return items
