"""MIDI derivation from cached STEM analyses.

Canonical invariant:
    original audio seconds are the master timeline.

Generated MIDI is derived data only. No MIDI generation function mutates
lyrics, chord, beat, measure, block, or audio timestamps.

Core tracks:
    vocals.wav -> vocal melody MIDI
    drums.wav  -> drum/rhythm MIDI
    harmony structure (other + bass evidence) -> chord MIDI

A combined format-1 MIDI is also available for A/B listening and later editor
integration.
"""

from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import librosa
import numpy as np


PPQ = 480
DEFAULT_TEMPO = 120.0
VOCAL_PROGRAM = 53     # GM Voice Oohs, zero-based
CHORD_PROGRAM = 27     # Clean Electric Guitar, zero-based
DRUM_CHANNEL = 9       # MIDI channel 10, zero-based

GM_KICK = 36
GM_SNARE = 38
GM_CLOSED_HH = 42

PC = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}


def _vlq(value: int) -> bytes:
    value = max(0, int(value))
    chunks = [value & 0x7F]
    value >>= 7
    while value:
        chunks.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(chunks))


def _tempo_values(tempo: float) -> tuple[float, int, float]:
    tempo = max(20.0, float(tempo or DEFAULT_TEMPO))
    us_per_quarter = int(round(60_000_000.0 / tempo))
    ticks_per_second = PPQ * tempo / 60.0
    return tempo, us_per_quarter, ticks_per_second


def _midi_track(events: list[tuple[int, int, bytes]], name: str) -> bytes:
    name_bytes = str(name).encode("utf-8")[:120]
    all_events = [
        (0, -10, b"\xFF\x03" + bytes([len(name_bytes)]) + name_bytes),
        *events,
    ]
    all_events.sort(key=lambda item: (int(item[0]), int(item[1])))

    track = bytearray()
    previous = 0
    for tick, _order, payload in all_events:
        tick = max(previous, int(tick))
        track.extend(_vlq(tick - previous))
        track.extend(payload)
        previous = tick

    track.extend(b"\x00\xFF\x2F\x00")
    return b"MTrk" + struct.pack(">I", len(track)) + bytes(track)


def _format0(events: list[tuple[int, int, bytes]], *, tempo: float, name: str) -> bytes:
    _tempo, us_per_quarter, _tps = _tempo_values(tempo)
    tempo_event = (0, -20, b"\xFF\x51\x03" + us_per_quarter.to_bytes(3, "big"))
    track = _midi_track([tempo_event, *events], name)
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ) + track


def _format1(
    tracks: list[tuple[str, list[tuple[int, int, bytes]]]],
    *,
    tempo: float,
) -> bytes:
    _tempo, us_per_quarter, _tps = _tempo_values(tempo)
    conductor = _midi_track(
        [(0, 0, b"\xFF\x51\x03" + us_per_quarter.to_bytes(3, "big"))],
        "EZScore Master",
    )
    chunks = [conductor]
    for name, events in tracks:
        chunks.append(_midi_track(events, name))
    return (
        b"MThd"
        + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
        + b"".join(chunks)
    )


def analyze_vocal_notes(
    vocals_path: Path,
    *,
    sample_rate: int = 16000,
) -> dict[str, Any]:
    """Extract monophonic vocal notes directly from cached vocals.wav."""
    y, sr = librosa.load(str(vocals_path), sr=int(sample_rate), mono=True)
    if y.size == 0:
        raise RuntimeError("vocals.wav vide.")

    frame_length = 2048
    hop_length = 256

    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
        fill_na=np.nan,
    )

    f0 = np.asarray(f0, dtype=float)
    voiced_flag = np.asarray(voiced_flag, dtype=bool)
    voiced_prob = np.asarray(voiced_prob, dtype=float)
    times = librosa.times_like(f0, sr=sr, hop_length=hop_length)

    valid = voiced_flag & np.isfinite(f0) & np.isfinite(voiced_prob) & (voiced_prob >= 0.48)
    midi_float = np.full(len(f0), np.nan, dtype=float)
    midi_float[valid] = librosa.hz_to_midi(f0[valid])

    # 7-frame median around valid values.
    smoothed = midi_float.copy()
    half = 3
    for i in range(len(smoothed)):
        lo = max(0, i - half)
        hi = min(len(smoothed), i + half + 1)
        finite = midi_float[lo:hi][np.isfinite(midi_float[lo:hi])]
        if finite.size:
            smoothed[i] = float(np.median(finite))

    notes: list[dict[str, Any]] = []
    current_note = None
    start_idx = None
    stable_candidate = None
    stable_start = None
    stable_frames = max(1, int(math.ceil(0.10 / (hop_length / sr))))

    def close(end_idx: int) -> None:
        nonlocal current_note, start_idx, stable_candidate, stable_start
        if current_note is None or start_idx is None or end_idx < start_idx:
            current_note = None
            start_idx = None
            stable_candidate = None
            stable_start = None
            return
        start = float(times[start_idx])
        end = float(times[min(end_idx, len(times) - 1)] + hop_length / sr)
        if end - start >= 0.09:
            probs = voiced_prob[start_idx:end_idx + 1]
            finite_probs = probs[np.isfinite(probs)]
            conf = float(np.mean(finite_probs)) if finite_probs.size else 0.0
            notes.append({
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(end - start, 6),
                "midi": int(np.clip(current_note, 0, 127)),
                "note": str(librosa.midi_to_note(int(np.clip(current_note, 0, 127)), unicode=False)),
                "confidence": round(conf, 4),
            })
        current_note = None
        start_idx = None
        stable_candidate = None
        stable_start = None

    for i, value in enumerate(smoothed):
        if not np.isfinite(value):
            if current_note is not None:
                close(i - 1)
            continue

        proposed = int(round(float(value)))
        if current_note is None:
            current_note = proposed
            start_idx = i
            continue

        if abs(float(value) - float(current_note)) < 0.70:
            stable_candidate = None
            stable_start = None
            continue

        if proposed == current_note:
            stable_candidate = None
            stable_start = None
            continue

        if stable_candidate != proposed:
            stable_candidate = proposed
            stable_start = i
            continue

        if stable_start is not None and (i - stable_start + 1) >= stable_frames:
            new_start = stable_start
            close(new_start - 1)
            current_note = proposed
            start_idx = new_start

    if current_note is not None:
        close(len(times) - 1)

    return {
        "source": "vocals.wav",
        "timebase": "original_audio_seconds",
        "sample_rate": int(sr),
        "hop_length": int(hop_length),
        "note_count": len(notes),
        "notes": notes,
    }


def build_vocal_midi(
    notes: list[dict[str, Any]],
    *,
    tempo: float,
    program: int = VOCAL_PROGRAM,
) -> bytes:
    _tempo, _us, tps = _tempo_values(tempo)
    events: list[tuple[int, int, bytes]] = [
        (0, 0, bytes([0xC0, int(program) & 0x7F]))
    ]
    for note in notes or []:
        start = max(0.0, float(note.get("start", 0.0) or 0.0))
        end = max(start + 0.04, float(note.get("end", start + 0.04) or start + 0.04))
        pitch = int(np.clip(int(note.get("midi", 60) or 60), 0, 127))
        confidence = float(note.get("confidence", 0.75) or 0.75)
        velocity = int(np.clip(round(55 + 55 * confidence), 40, 112))
        t0 = int(round(start * tps))
        t1 = int(round(end * tps))
        events.append((t0, 2, bytes([0x90, pitch, velocity])))
        events.append((t1, 1, bytes([0x80, pitch, 0])))
    return _format0(events, tempo=tempo, name="EZScore Vocal")


def _parse_chord(symbol: str) -> list[int]:
    text = str(symbol or "").strip()
    if not text or text in {".", "-", "N"}:
        return []

    text = text.replace("♭", "b").replace("♯", "#")
    m = __import__("re").match(r"^([A-Ga-g])([#b]?)(.*)$", text)
    if not m:
        return []

    root_name = (m.group(1).upper() + m.group(2)).upper()
    if root_name not in PC:
        return []
    root = PC[root_name]
    tail = m.group(3).lower()

    minor = tail.startswith("m") and not tail.startswith("maj")
    diminished = "dim" in tail or "°" in tail
    sus2 = "sus2" in tail
    sus4 = "sus" in tail and not sus2

    if diminished:
        intervals = [0, 3, 6]
    elif sus2:
        intervals = [0, 2, 7]
    elif sus4:
        intervals = [0, 5, 7]
    elif minor:
        intervals = [0, 3, 7]
    else:
        intervals = [0, 4, 7]

    if "7" in tail:
        if "maj7" in tail:
            intervals.append(11)
        else:
            intervals.append(10)

    base = 48 + root
    return [int(np.clip(base + interval, 0, 127)) for interval in intervals]


def chord_events_from_structure(
    structure: dict[str, Any],
    *,
    tempo: float,
    program: int = CHORD_PROGRAM,
) -> list[tuple[int, int, bytes]]:
    """Build chord MIDI from existing measure/beat timestamps, never re-quantized."""
    _tempo, _us, tps = _tempo_values(tempo)
    measures = list(structure.get("measures", []) or [])
    events: list[tuple[int, int, bytes]] = [
        (0, 0, bytes([0xC1, int(program) & 0x7F]))
    ]

    for measure in measures:
        t0 = float(measure.get("time_start", 0.0) or 0.0)
        t1 = max(t0 + 0.05, float(measure.get("time_end", t0 + 0.05) or t0 + 0.05))
        chords = list(measure.get("beat_chords", []) or [])
        if not chords:
            continue
        beat_duration = (t1 - t0) / len(chords)
        for index, chord in enumerate(chords):
            pitches = _parse_chord(str(chord))
            if not pitches:
                continue
            start = t0 + index * beat_duration
            end = min(t1, start + beat_duration * 0.86)
            tick0 = int(round(start * tps))
            tick1 = int(round(end * tps))
            for pitch in pitches:
                events.append((tick0, 2, bytes([0x91, pitch, 82])))
                events.append((tick1, 1, bytes([0x81, pitch, 0])))
    return events


def build_chord_midi(
    structure: dict[str, Any],
    *,
    tempo: float,
    program: int = CHORD_PROGRAM,
) -> bytes:
    events = chord_events_from_structure(structure, tempo=tempo, program=program)
    return _format0(events, tempo=tempo, name="EZScore Chords")


def analyze_drum_beats(drums_path: Path) -> dict[str, Any]:
    """Detect beat positions directly from drums.wav on original-audio seconds."""
    y, sr = librosa.load(str(drums_path), sr=22050, mono=True)
    if y.size == 0:
        raise RuntimeError("drums.wav vide.")

    hop = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop,
        trim=False,
    )
    tempo_value = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
    frames = np.asarray(beat_frames, dtype=int)
    times = librosa.frames_to_time(frames, sr=sr, hop_length=hop)

    strengths = onset_env[np.clip(frames, 0, max(0, len(onset_env) - 1))] if len(frames) else np.array([])
    if strengths.size:
        p50 = float(np.percentile(strengths, 50))
        p75 = float(np.percentile(strengths, 75))
    else:
        p50 = p75 = 0.0

    beats = []
    for i, t in enumerate(times):
        strength = float(strengths[i]) if i < len(strengths) else 0.0
        beats.append({
            "index": int(i),
            "time": round(float(t), 6),
            "strength": round(strength, 6),
            "strong": bool(strength >= p75),
            "medium": bool(strength >= p50),
        })

    return {
        "source": "drums.wav",
        "timebase": "original_audio_seconds",
        "tempo": round(tempo_value, 4),
        "beat_count": len(beats),
        "beats": beats,
    }


def drum_events(
    drum_analysis: dict[str, Any],
    *,
    tempo: float,
    beats_per_bar: int = 4,
) -> list[tuple[int, int, bytes]]:
    """Create an audition-oriented GM drum track aligned to detected beat times."""
    _tempo, _us, tps = _tempo_values(tempo)
    beats = list(drum_analysis.get("beats", []) or [])
    bpb = max(2, int(beats_per_bar or 4))
    events: list[tuple[int, int, bytes]] = []

    for item in beats:
        i = int(item.get("index", 0) or 0)
        t = max(0.0, float(item.get("time", 0.0) or 0.0))
        strong = bool(item.get("strong", False))
        medium = bool(item.get("medium", False))

        # Every beat gets a light closed hi-hat.
        notes = [(GM_CLOSED_HH, 58)]

        # Audition pattern: downbeat/strong beat -> kick, middle/backbeat -> snare.
        position = i % bpb
        if position == 0 or strong:
            notes.append((GM_KICK, 92 if strong else 82))
        elif (bpb == 4 and position == 2) or medium:
            notes.append((GM_SNARE, 78))

        tick0 = int(round(t * tps))
        tick1 = tick0 + max(1, int(round(0.06 * tps)))
        for pitch, velocity in notes:
            events.append((tick0, 2, bytes([0x99, pitch & 0x7F, velocity & 0x7F])))
            events.append((tick1, 1, bytes([0x89, pitch & 0x7F, 0])))

    return events


def build_drum_midi(
    drum_analysis: dict[str, Any],
    *,
    tempo: float,
    beats_per_bar: int = 4,
) -> bytes:
    events = drum_events(
        drum_analysis,
        tempo=tempo,
        beats_per_bar=beats_per_bar,
    )
    return _format0(events, tempo=tempo, name="EZScore Drums")


def build_combined_midi(
    *,
    vocal_notes: list[dict[str, Any]],
    structure: dict[str, Any],
    drum_analysis: dict[str, Any],
    tempo: float,
    beats_per_bar: int = 4,
) -> bytes:
    """Format-1 file: vocals + chords + drums, all on original-audio seconds."""
    _tempo, _us, tps = _tempo_values(tempo)

    vocal_events: list[tuple[int, int, bytes]] = [
        (0, 0, bytes([0xC0, VOCAL_PROGRAM]))
    ]
    for note in vocal_notes or []:
        start = max(0.0, float(note.get("start", 0.0) or 0.0))
        end = max(start + 0.04, float(note.get("end", start + 0.04) or start + 0.04))
        pitch = int(np.clip(int(note.get("midi", 60) or 60), 0, 127))
        conf = float(note.get("confidence", 0.75) or 0.75)
        vel = int(np.clip(round(55 + 55 * conf), 40, 112))
        vocal_events.append((int(round(start * tps)), 2, bytes([0x90, pitch, vel])))
        vocal_events.append((int(round(end * tps)), 1, bytes([0x80, pitch, 0])))

    chord_events = chord_events_from_structure(
        structure,
        tempo=tempo,
        program=CHORD_PROGRAM,
    )
    drums = drum_events(
        drum_analysis,
        tempo=tempo,
        beats_per_bar=beats_per_bar,
    )

    return _format1(
        [
            ("Vocal", vocal_events),
            ("Chords", chord_events),
            ("Drums", drums),
        ],
        tempo=tempo,
    )


def generate_stem_midi_bundle(
    *,
    vocals_path: Path,
    drums_path: Path,
    structure: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Generate/cache the 3 core MIDI tracks plus a combined multitrack MIDI."""
    output_dir.mkdir(parents=True, exist_ok=True)

    tempo = float(structure.get("tempo", 0.0) or 0.0)
    if tempo <= 1.0:
        drum_probe = analyze_drum_beats(drums_path)
        tempo = float(drum_probe.get("tempo", 0.0) or DEFAULT_TEMPO)
    else:
        drum_probe = analyze_drum_beats(drums_path)

    bpb = int(structure.get("beats_per_bar", 4) or 4)

    vocal = analyze_vocal_notes(vocals_path)
    drums = drum_probe

    vocal_path = output_dir / "vocal.mid"
    chords_path = output_dir / "chords.mid"
    drums_path_out = output_dir / "drums.mid"
    combined_path = output_dir / "stem_mix.mid"

    vocal_path.write_bytes(build_vocal_midi(vocal["notes"], tempo=tempo))
    chords_path.write_bytes(build_chord_midi(structure, tempo=tempo))
    drums_path_out.write_bytes(build_drum_midi(drums, tempo=tempo, beats_per_bar=bpb))
    combined_path.write_bytes(
        build_combined_midi(
            vocal_notes=vocal["notes"],
            structure=structure,
            drum_analysis=drums,
            tempo=tempo,
            beats_per_bar=bpb,
        )
    )

    browser_events = browser_events_from_bundle(
        vocal_notes=vocal["notes"],
        structure=structure,
        drum_analysis=drums,
        beats_per_bar=bpb,
    )

    metadata = {
        "timebase": "original_audio_seconds",
        "tempo": tempo,
        "beats_per_bar": bpb,
        "vocal_note_count": int(vocal.get("note_count", 0)),
        "drum_beat_count": int(drums.get("beat_count", 0)),
        "files": {
            "vocal": vocal_path.name,
            "chords": chords_path.name,
            "drums": drums_path_out.name,
            "combined": combined_path.name,
        },
        "browser_events": browser_events,
        "vocal_analysis": vocal,
        "drum_analysis": drums,
    }
    (output_dir / "stem_midi.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def _job_status_path(output_dir: Path) -> Path:
    return Path(output_dir) / "job_status.json"


def load_stem_midi_job(output_dir: Path) -> dict[str, Any]:
    path = _job_status_path(output_dir)
    if not path.is_file():
        return {"state": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"state": "unknown"}


def launch_stem_midi_job(
    *,
    vocals_path: Path,
    drums_path: Path,
    structure_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Launch heavy STEM->MIDI work outside the Streamlit request thread."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    previous = load_stem_midi_job(output_dir)
    if str(previous.get("state", "")) in {"starting", "running"}:
        return previous

    status_path = _job_status_path(output_dir)
    log_path = output_dir / "job.log"
    status_path.write_text(
        json.dumps(
            {
                "state": "starting",
                "pid": None,
                "message": "Préparation du processus MIDI…",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "ezscore.analysis.stem_midi_worker",
        "--vocals",
        str(Path(vocals_path)),
        "--drums",
        str(Path(drums_path)),
        "--structure",
        str(Path(structure_path)),
        "--output",
        str(output_dir),
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

    with open(log_path, "ab", buffering=0) as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).resolve().parents[2]),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=(os.name != "nt"),
            creationflags=creationflags,
        )

    payload = {
        "state": "running",
        "pid": int(proc.pid),
        "message": "Génération MIDI en cours dans un processus séparé.",
        "log": str(log_path),
    }
    status_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def browser_events_from_bundle(
    *,
    vocal_notes: list[dict[str, Any]],
    structure: dict[str, Any],
    drum_analysis: dict[str, Any],
    beats_per_bar: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Return real-time browser MIDI events on canonical audio seconds.

    This representation is intentionally independent from SMF tick conversion.
    The original audio remains the master clock in the browser player.
    """
    vocal_events: list[dict[str, Any]] = [{
        "time": 0.0,
        "kind": "program",
        "channel": 0,
        "program": VOCAL_PROGRAM,
    }]
    for note in vocal_notes or []:
        start = max(0.0, float(note.get("start", 0.0) or 0.0))
        end = max(start + 0.04, float(note.get("end", start + 0.04) or start + 0.04))
        pitch = int(np.clip(int(note.get("midi", 60) or 60), 0, 127))
        conf = float(note.get("confidence", 0.75) or 0.75)
        vel = int(np.clip(round(55 + 55 * conf), 40, 112))
        vocal_events.append({
            "time": start, "kind": "note_on", "channel": 0,
            "note": pitch, "velocity": vel,
        })
        vocal_events.append({
            "time": end, "kind": "note_off", "channel": 0,
            "note": pitch, "velocity": 0,
        })

    chord_events_browser: list[dict[str, Any]] = [{
        "time": 0.0,
        "kind": "program",
        "channel": 1,
        "program": CHORD_PROGRAM,
    }]
    measures = list(structure.get("measures", []) or [])
    for measure in measures:
        t0 = float(measure.get("time_start", 0.0) or 0.0)
        t1 = max(t0 + 0.05, float(measure.get("time_end", t0 + 0.05) or t0 + 0.05))
        chords = list(measure.get("beat_chords", []) or [])
        if not chords:
            continue
        beat_duration = (t1 - t0) / len(chords)
        for index, chord in enumerate(chords):
            pitches = _parse_chord(str(chord))
            if not pitches:
                continue
            start = t0 + index * beat_duration
            end = min(t1, start + beat_duration * 0.86)
            for pitch in pitches:
                chord_events_browser.append({
                    "time": start, "kind": "note_on", "channel": 1,
                    "note": int(pitch), "velocity": 82,
                })
                chord_events_browser.append({
                    "time": end, "kind": "note_off", "channel": 1,
                    "note": int(pitch), "velocity": 0,
                })

    drum_events_browser: list[dict[str, Any]] = []
    beats = list(drum_analysis.get("beats", []) or [])
    bpb = max(2, int(beats_per_bar or 4))
    for item in beats:
        i = int(item.get("index", 0) or 0)
        t = max(0.0, float(item.get("time", 0.0) or 0.0))
        strong = bool(item.get("strong", False))
        medium = bool(item.get("medium", False))
        notes = [(GM_CLOSED_HH, 58)]
        position = i % bpb
        if position == 0 or strong:
            notes.append((GM_KICK, 92 if strong else 82))
        elif (bpb == 4 and position == 2) or medium:
            notes.append((GM_SNARE, 78))
        for pitch, velocity in notes:
            drum_events_browser.append({
                "time": t, "kind": "note_on", "channel": DRUM_CHANNEL,
                "note": pitch, "velocity": velocity,
            })
            drum_events_browser.append({
                "time": t + 0.06, "kind": "note_off", "channel": DRUM_CHANNEL,
                "note": pitch, "velocity": 0,
            })

    priority = {"program": 0, "note_off": 1, "note_on": 2}
    for events in (vocal_events, chord_events_browser, drum_events_browser):
        events.sort(
            key=lambda e: (
                float(e.get("time", 0.0)),
                priority.get(str(e.get("kind", "")), 9),
                int(e.get("note", 0) or 0),
            )
        )

    return {
        "vocal": vocal_events,
        "chords": chord_events_browser,
        "drums": drum_events_browser,
    }
