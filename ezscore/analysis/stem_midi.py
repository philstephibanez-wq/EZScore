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
import time
from pathlib import Path
from typing import Any

import librosa
import numpy as np

from ezscore.analysis.vocal import (
    VOCAL_CONFIDENCE_DEMUCS,
    _recover_continuous_weak_voicing,
    _segment_notes,
)


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
    chunk_seconds: float = 20.0,
    overlap_seconds: float = 1.0,
    progress_callback=None,
) -> dict[str, Any]:
    """Chunked pYIN with overlap + mature EZScore voicing/segmentation."""
    y, sr = librosa.load(str(vocals_path), sr=int(sample_rate), mono=True)
    if y.size == 0:
        raise RuntimeError("vocals.wav vide.")

    frame_length = 2048
    hop_length = 256
    core_samples = max(frame_length * 4, int(round(float(chunk_seconds) * sr)))
    overlap_samples = max(0, int(round(float(overlap_seconds) * sr)))
    total_chunks = max(1, int(math.ceil(len(y) / core_samples)))
    duration = float(len(y) / sr)

    if progress_callback:
        progress_callback({
            "stage": "vocal_load_done",
            "message": "vocals.wav chargé.",
            "duration_seconds": round(duration, 3),
            "samples": int(len(y)),
            "sample_rate": int(sr),
            "chunk_seconds": float(chunk_seconds),
            "overlap_seconds": float(overlap_seconds),
            "chunk_total": int(total_chunks),
            "percent": 0.0,
        })

    time_parts = []
    midi_parts = []
    prob_parts = []

    for chunk_index in range(total_chunks):
        core_start = chunk_index * core_samples
        core_end = min(len(y), (chunk_index + 1) * core_samples)
        analysis_start = max(0, core_start - overlap_samples)
        analysis_end = min(len(y), core_end + overlap_samples)
        chunk = y[analysis_start:analysis_end]

        if progress_callback:
            progress_callback({
                "stage": "vocal_pyin",
                "message": (
                    f"pYIN chant : segment {chunk_index + 1}/{total_chunks} "
                    f"({core_start / sr:.1f}s → {core_end / sr:.1f}s)"
                ),
                "chunk_index": int(chunk_index + 1),
                "chunk_total": int(total_chunks),
                "time_start": round(float(core_start / sr), 3),
                "time_end": round(float(core_end / sr), 3),
                "percent": round(chunk_index / total_chunks, 4),
            })

        f0, voiced_flag, voiced_prob = librosa.pyin(
            chunk,
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

        rms = librosa.feature.rms(
            y=chunk,
            frame_length=frame_length,
            hop_length=hop_length,
            center=True,
        )[0]
        if len(rms) < len(f0):
            rms = np.pad(rms, (0, len(f0)-len(rms)), mode="edge" if len(rms) else "constant")
        elif len(rms) > len(f0):
            rms = rms[:len(f0)]

        strong_valid = (
            voiced_flag & np.isfinite(f0) & np.isfinite(voiced_prob)
            & (voiced_prob >= float(VOCAL_CONFIDENCE_DEMUCS))
        )
        valid = _recover_continuous_weak_voicing(
            f0=f0,
            voiced_flag=voiced_flag,
            voiced_prob=voiced_prob,
            rms=np.asarray(rms, dtype=float),
            confidence_floor=float(VOCAL_CONFIDENCE_DEMUCS),
            strong_valid=strong_valid,
        )
        midi_float = np.full(len(f0), np.nan, dtype=float)
        midi_float[valid] = librosa.hz_to_midi(f0[valid])

        absolute_times = librosa.times_like(f0, sr=sr, hop_length=hop_length) + float(analysis_start / sr)
        core_t0 = float(core_start / sr)
        core_t1 = float(core_end / sr)
        keep = ((absolute_times >= core_t0) &
                ((absolute_times < core_t1) if chunk_index + 1 < total_chunks else (absolute_times <= core_t1 + 1e-6)))
        time_parts.append(absolute_times[keep])
        midi_parts.append(midi_float[keep])
        prob_parts.append(voiced_prob[keep])

        if progress_callback:
            progress_callback({
                "stage": "vocal_pyin",
                "message": f"pYIN chant : segment {chunk_index + 1}/{total_chunks} terminé.",
                "chunk_index": int(chunk_index + 1),
                "chunk_total": int(total_chunks),
                "percent": round((chunk_index + 1) / total_chunks, 4),
            })

    times = np.concatenate(time_parts) if time_parts else np.array([], dtype=float)
    midi_float = np.concatenate(midi_parts) if midi_parts else np.array([], dtype=float)
    voiced_prob = np.concatenate(prob_parts) if prob_parts else np.array([], dtype=float)

    notes = _segment_notes(
        times=times,
        midi_float=midi_float,
        voiced_prob=voiced_prob,
        hop_seconds=float(hop_length) / float(sr),
    )

    if progress_callback:
        progress_callback({
            "stage": "vocal_notes_done",
            "message": f"Analyse chant terminée : {len(notes)} notes.",
            "note_count": int(len(notes)),
            "percent": 1.0,
        })

    return {
        "source": "vocals.wav",
        "engine": "pyin-v3-adaptive-voicing-chunked-overlap",
        "timebase": "original_audio_seconds",
        "sample_rate": int(sr),
        "hop_length": int(hop_length),
        "chunk_seconds": float(chunk_seconds),
        "overlap_seconds": float(overlap_seconds),
        "chunk_count": int(total_chunks),
        "confidence_floor": float(VOCAL_CONFIDENCE_DEMUCS),
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


def analyze_drum_beats(
    drums_path: Path,
    *,
    progress_callback=None,
) -> dict[str, Any]:
    """Detect beat positions from drums.wav with observable heavy stages."""
    if progress_callback:
        progress_callback({
            "stage": "drums_load",
            "message": "Batterie : chargement drums.wav…",
            "percent": 0.05,
        })

    y, sr = librosa.load(str(drums_path), sr=22050, mono=True)
    if y.size == 0:
        raise RuntimeError("drums.wav vide.")

    if progress_callback:
        progress_callback({
            "stage": "drums_onset",
            "message": "Batterie : calcul de l'enveloppe d'attaque…",
            "percent": 0.25,
            "samples": int(y.size),
            "sample_rate": int(sr),
            "duration_seconds": round(float(y.size / sr), 3),
        })

    hop = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)

    if progress_callback:
        progress_callback({
            "stage": "drums_beat_track",
            "message": "Batterie : détection tempo / beats…",
            "percent": 0.55,
            "onset_frames": int(len(onset_env)),
        })

    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop,
        trim=False,
    )

    tempo_value = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
    frames = np.asarray(beat_frames, dtype=int)
    times = librosa.frames_to_time(frames, sr=sr, hop_length=hop)

    if progress_callback:
        progress_callback({
            "stage": "drums_postprocess",
            "message": "Batterie : classement des temps détectés…",
            "percent": 0.80,
            "beat_count": int(len(frames)),
            "tempo": round(tempo_value, 4),
        })

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

    result = {
        "source": "drums.wav",
        "timebase": "original_audio_seconds",
        "tempo": round(tempo_value, 4),
        "beat_count": len(beats),
        "beats": beats,
    }

    if progress_callback:
        progress_callback({
            "stage": "done",
            "message": f"Batterie terminée : {len(beats)} beats.",
            "percent": 1.0,
            "beat_count": int(len(beats)),
            "tempo": round(tempo_value, 4),
        })
    return result


def drum_analysis_from_structure(structure: dict[str, Any]) -> dict[str, Any]:
    """Build metric drum events from persisted beat timestamps; no audio re-analysis."""
    timeline = list(structure.get("beat_timeline", []) or [])
    if not timeline:
        raise RuntimeError(
            "La structure ne contient pas de beat_timeline canonique. "
            "Recalculer Blocs / structure avant le MIDI."
        )

    bpb = max(2, int(structure.get("beats_per_bar", 4) or 4))
    beats = []
    for index, item in enumerate(timeline):
        pos = index % bpb
        strong = pos == 0
        if bpb == 2:
            medium = pos == 1
        elif bpb == 4:
            medium = pos == 2
        elif bpb == 6:
            medium = pos == 3
        else:
            medium = False
        beats.append({
            "index": int(index),
            "time": round(float(item.get("time", 0.0) or 0.0), 6),
            "strength": float(item.get("strength", 0.0) or 0.0),
            "strong": bool(strong),
            "medium": bool(medium),
            "metric_position": int(pos),
            "measure_index": int(index // bpb),
        })

    return {
        "source": "structure.beat_timeline",
        "timebase": "original_audio_seconds",
        "tempo": float(structure.get("tempo", 0.0) or 0.0),
        "beat_count": len(beats),
        "beats_per_bar": bpb,
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


def _pid_is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but cannot be signalled by this user.
        return True
    except OSError:
        return False
    return True


def _job_status_path(output_dir: Path) -> Path:
    return Path(output_dir) / "job_status.json"


def _terminate_pid(pid: int) -> None:
    value = int(pid)
    if value <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(value), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        os.kill(value, 15)


def load_stem_midi_job(output_dir: Path) -> dict[str, Any]:
    path = _job_status_path(output_dir)
    if not path.is_file():
        return {"state": "idle"}

    payload = json.loads(path.read_text(encoding="utf-8"))
    state = str(payload.get("state", "") or "")
    pid = payload.get("pid")

    if state in {"starting", "running"}:
        if pid is not None and not _pid_is_alive(pid):
            stale = dict(payload)
            stale.update({
                "state": "error",
                "stage": "worker_dead",
                "message": (
                    f"Le worker MIDI PID {pid} n'existe plus alors que le job "
                    "était encore marqué en cours."
                ),
            })
            path.write_text(
                json.dumps(stale, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return stale

        updated = float(payload.get("updated_at_epoch", 0.0) or 0.0)
        age = max(0.0, time.time() - updated) if updated > 0 else 0.0
        if age > 150.0 and pid is not None:
            _terminate_pid(int(pid))
            stale = dict(payload)
            stale.update({
                "state": "error",
                "stage": "worker_stalled",
                "message": (
                    f"Worker MIDI bloqué : aucun statut actualisé depuis "
                    f"{age:.0f}s. Le processus PID {pid} a été arrêté."
                ),
            })
            path.write_text(
                json.dumps(stale, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return stale

    return payload


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
