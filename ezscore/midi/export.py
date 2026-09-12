"""Standard MIDI File export for EZScore editor events."""

from __future__ import annotations

import struct

from .events import build_chord_midi_events


def _vlq(value: int) -> bytes:
    value = max(0, int(value))
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(chunks))


def build_midi_file(
    beats,
    tempo,
    signature: str = "4/4",
    beats_per_measure: int = 4,
    program: int = 27,
    gate_ratio: float = 0.48,
    strum_ms: float = 12.0,
) -> bytes:
    """Create a format-0 GM MIDI using the same events as browser playback."""
    ppq = 480
    tempo = max(20.0, float(tempo or 120.0))
    us_per_quarter = int(round(60_000_000.0 / tempo))
    ticks_per_second = ppq * tempo / 60.0

    midi_events = build_chord_midi_events(
        beats=beats,
        signature=signature,
        beats_per_measure=beats_per_measure,
        program=program,
        gate_ratio=gate_ratio,
        strum_ms=strum_ms,
    )

    events = [
        (0, 0, b"\xFF\x51\x03" + us_per_quarter.to_bytes(3, "big")),
        (0, 0, b"\xFF\x03\x0eEZScore Chords"),
    ]

    for event in midi_events:
        tick = max(0, int(round(float(event["time"]) * ticks_per_second)))
        if event["kind"] == "program":
            payload = bytes([int(event["status"]) & 0xFF, int(event["data1"]) & 0x7F])
            order = 0
        else:
            payload = bytes([
                int(event["status"]) & 0xFF,
                int(event["data1"]) & 0x7F,
                int(event.get("data2", 0) or 0) & 0x7F,
            ])
            order = 1 if event["kind"] == "note_off" else 2
        events.append((tick, order, payload))

    events.sort(key=lambda item: (item[0], item[1]))
    track = bytearray()
    previous_tick = 0
    for tick, _order, payload in events:
        track.extend(_vlq(int(tick) - previous_tick))
        track.extend(payload)
        previous_tick = int(tick)
    track.extend(b"\x00\xFF\x2F\x00")

    return (
        b"MThd"
        + struct.pack(">IHHH", 6, 0, 1, ppq)
        + b"MTrk"
        + struct.pack(">I", len(track))
        + bytes(track)
    )
