"""STEM_LAB-style analysis surface embedded in EZScore.

This is deliberately isolated from the historical EZScore analyzer.
It preserves the validated workflow:

    original -> Whisper small -> lyrics
    vocals   -> vocal melody / F0
    drums    -> tempo / beats / measures
    bass     -> auxiliary root evidence
    other    -> harmony / chords

All timestamps are seconds on the original-audio timebase.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import librosa
import streamlit as st
import torch
import whisper

from ezscore.analysis.stems import (
    DEFAULT_DEMUCS_MODEL,
    STEM_NAMES,
    cached_stem_paths,
    demucs_available,
    ensure_stems,
    load_stem_manifest,
    stems_cache_complete,
)
from ezscore.analysis.chords_quality import (
    analyze_chords_absolute,
    chord_for_interval,
    quality_chord_engine_available,
)
from ezscore.analysis.rhythm_quality import (
    analyze_beats as analyze_quality_beats,
    quality_rhythm_engine_available,
)
import ezscore.persistence as _persistence
from ezscore.analysis.stem_midi import (
    browser_events_from_bundle,
    launch_stem_midi_job,
    load_stem_midi_job,
    _read_json_with_retry,
)

from ezscore.midi.stem_sync_player import render_stem_midi_sync_player
from ezscore.ui.chords_lyrics_editor import render_chords_lyrics_editor
from ezscore.player.stem_webaudio import (
    ffmpeg_available as _stem_ffmpeg_available,
    make_browser_preview as _make_browser_preview,
    render_player as _render_stem_player,
)


APP_DIR = Path(__file__).resolve().parents[2]
LAB_CACHE_DIR = APP_DIR / "data" / "analysis" / "stem_lab"
MIN_VISUAL_BLOCK_MEASURES = 4


def _work_dir(audio_hash: str) -> Path:
    path = LAB_CACHE_DIR / str(audio_hash)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _song_for_hash(audio_hash: str) -> dict[str, Any]:
    for item in _persistence.list_song_catalog(sort_by="title"):
        if str(item.get("audio_hash", "")) == str(audio_hash):
            return dict(item)
    return {}


def _source_path(audio_hash: str, song: dict[str, Any]) -> Path | None:
    filename = str(song.get("original_filename", "") or "").strip()
    audio_dir = getattr(_persistence, "AUDIO_DIR", None)
    if filename and audio_dir is not None:
        candidate = Path(audio_dir) / Path(filename).name
        if candidate.is_file():
            return candidate
    found = _persistence.find_persisted_audio(audio_hash)
    return Path(found) if found else None


def _speech_cache_path(audio_hash: str) -> Path:
    return _work_dir(audio_hash) / "whisper_original_small.json"


def _load_speech(audio_hash: str) -> dict[str, Any] | None:
    path = _speech_cache_path(audio_hash)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_resource(show_spinner=False)
def _whisper_small(device: str):
    return whisper.load_model("small", device=device)


def _transcribe_original(source: Path, audio_hash: str) -> dict[str, Any]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = _whisper_small(device)
    result = model.transcribe(
        str(source),
        word_timestamps=True,
        fp16=(device == "cuda"),
        verbose=False,
    )
    words: list[dict[str, Any]] = []
    for segment in result.get("segments", []) or []:
        for word in segment.get("words", []) or []:
            text = str(word.get("word", "") or "").strip()
            start = float(word.get("start", 0.0) or 0.0)
            end = float(word.get("end", start) or start)
            if text and end > start:
                words.append({"start": start, "end": end, "text": text})

    payload = {
        "engine": "openai-whisper",
        "model": "small",
        "source": "original",
        "language": str(result.get("language", "") or ""),
        "text": str(result.get("text", "") or "").strip(),
        "words": words,
    }
    _speech_cache_path(audio_hash).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _download_stems(stems: dict[str, Path]) -> None:
    labels = {
        "vocals": "Chant",
        "drums": "Batterie",
        "bass": "Basse",
        "other": "Other",
    }
    cols = st.columns(4)
    for col, name in zip(cols, STEM_NAMES):
        with col:
            path = stems.get(name)
            if path is None:
                st.button(
                    f"{labels[name]} absent",
                    disabled=True,
                    width="stretch",
                    key=f"ezstem_missing_{name}",
                )
            else:
                st.download_button(
                    f"⬇ {labels[name]}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="audio/wav",
                    width="stretch",
                    key=f"ezstem_download_{name}_{path.stat().st_size}",
                )


_PC_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_MAJOR = np.zeros(12, dtype=float)
_MAJOR[[0, 4, 7]] = [1.0, 0.82, 0.88]
_MINOR = np.zeros(12, dtype=float)
_MINOR[[0, 3, 7]] = [1.0, 0.82, 0.88]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 1e-9 or nb <= 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _templates():
    out = []
    for root in range(12):
        out.append((_PC_NAMES[root], np.roll(_MAJOR, root), root))
        out.append((_PC_NAMES[root] + "m", np.roll(_MINOR, root), root))
    return out


_CHORD_TEMPLATES = _templates()


def _estimate_chord(chroma: np.ndarray, bass: np.ndarray | None) -> str:
    c = np.asarray(chroma, dtype=float)
    if not np.any(np.isfinite(c)) or float(np.sum(c)) <= 1e-8:
        return "N"
    c = np.nan_to_num(c, nan=0.0)
    c = c / max(1e-8, float(np.max(c)))

    b = None
    if bass is not None:
        b = np.nan_to_num(np.asarray(bass, dtype=float), nan=0.0)
        if float(np.sum(b)) > 1e-8:
            b = b / max(1e-8, float(np.max(b)))
        else:
            b = None

    best_name = "N"
    best_score = -1.0
    for name, template, root in _CHORD_TEMPLATES:
        score = _cosine(c, template)
        # Same STEM_LAB principle: bass is only weak root support.
        if b is not None:
            score = (0.90 * score) + (0.10 * float(b[root]))
        if score > best_score:
            best_score = score
            best_name = name
    return best_name


def _structure_cache_path(audio_hash: str) -> Path:
    return _work_dir(audio_hash) / "structure_analysis.json"


def _chord_cache_path(audio_hash: str) -> Path:
    return _work_dir(audio_hash) / "chord_analysis_lv_chordia.json"



def _coalesce_boundaries(
    boundaries: list[int],
    *,
    measure_count: int,
    min_measures: int = MIN_VISUAL_BLOCK_MEASURES,
) -> list[int]:
    """Reject only boundaries that would create micro-blocks.

    This is not fixed 4-bar slicing: recurrence-derived boundaries remain the
    source of structure. The minimum only prevents 1–3 measure visual blocks.
    """
    count = max(0, int(measure_count))
    if count <= 0:
        return []

    minimum = max(2, int(min_measures))
    candidates = sorted({1, *[int(x) for x in boundaries if 1 <= int(x) <= count]})
    kept = [1]

    for boundary in candidates[1:]:
        if boundary - kept[-1] >= minimum:
            kept.append(boundary)

    while len(kept) > 1 and (count - kept[-1] + 1) < minimum:
        kept.pop()

    return kept


def _build_visual_blocks(
    *,
    boundaries: list[int],
    measures: list[dict[str, Any]],
    words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not measures:
        return []

    starts = _coalesce_boundaries(
        boundaries,
        measure_count=len(measures),
        min_measures=MIN_VISUAL_BLOCK_MEASURES,
    )
    if not starts:
        starts = [1]

    earliest_word = min(
        (float(w.get("start", 0.0)) for w in words),
        default=None,
    )
    latest_word = max(
        (float(w.get("end", w.get("start", 0.0))) for w in words),
        default=None,
    )

    blocks: list[dict[str, Any]] = []
    for idx, m0 in enumerate(starts):
        m1 = starts[idx + 1] - 1 if idx + 1 < len(starts) else len(measures)
        first = measures[m0 - 1]
        last = measures[m1 - 1]
        t0 = float(first["time_start"])
        t1 = float(last["time_end"])

        if idx == 0 and earliest_word is not None:
            t0 = min(t0, earliest_word)
        if idx == len(starts) - 1 and latest_word is not None:
            t1 = max(t1, latest_word)

        block_words = [
            str(w.get("text", "") or "").strip()
            for w in words
            if float(w.get("end", 0.0) or 0.0) > t0
            and float(w.get("start", 0.0) or 0.0) < t1
        ]
        blocks.append({
            "cluster": chr(ord("A") + (idx % 26)),
            "measure_start": int(m0),
            "measure_end": int(m1),
            "measure_count": int(m1 - m0 + 1),
            "time_start": t0,
            "time_end": t1,
            "lyrics": " ".join(x for x in block_words if x),
            "chord_patterns": [
                measures[n - 1]["pattern"]
                for n in range(m0, m1 + 1)
            ],
            "visual_only": True,
        })
    return blocks


def _parse_signature(value: str) -> tuple[int, int]:
    text = str(value or "").strip()
    match = __import__("re").fullmatch(r"(\d+)\s*/\s*(\d+)", text)
    if not match:
        raise ValueError(
            "Signature invalide. Format attendu : N/D, par exemple 6/8, 9/8, 5/4."
        )
    numerator = int(match.group(1))
    denominator = int(match.group(2))
    if numerator < 1 or denominator < 1:
        raise ValueError("Le numérateur et le dénominateur doivent être positifs.")
    return numerator, denominator


def _default_grouping(numerator: int, denominator: int) -> list[int]:
    n = int(numerator)
    d = int(denominator)

    # Compound meters: 6/8, 9/8, 12/8, 15/8, ...
    if d >= 8 and n > 3 and n % 3 == 0:
        return [3] * (n // 3)

    # Common asymmetric eighth-note meters.
    if d >= 8 and n == 5:
        return [2, 3]
    if d >= 8 and n == 7:
        return [2, 2, 3]

    # Simple/odd quarter-note meters. Grouping controls accents, not bar length.
    if d == 4 and n == 5:
        return [3, 2]
    if d == 4 and n == 7:
        return [4, 3]

    return [1] * n


def _parse_grouping(
    value: str,
    *,
    numerator: int,
    denominator: int,
) -> list[int]:
    text = str(value or "").strip()
    if not text:
        return _default_grouping(numerator, denominator)

    parts = [part.strip() for part in text.split("+") if part.strip()]
    try:
        groups = [int(part) for part in parts]
    except ValueError as exc:
        raise ValueError(
            "Groupement invalide. Exemple : 3+3, 3+3+3, 3+2, 4+3."
        ) from exc

    if not groups or any(group < 1 for group in groups):
        raise ValueError("Chaque groupe métrique doit être supérieur ou égal à 1.")

    if sum(groups) != int(numerator):
        raise ValueError(
            f"Le groupement {text!r} totalise {sum(groups)}, "
            f"mais la signature a un numérateur de {int(numerator)}."
        )
    return groups


def _meter_spec(signature: str, grouping: str = "") -> dict[str, Any]:
    numerator, denominator = _parse_signature(signature)
    groups = _parse_grouping(
        grouping,
        numerator=numerator,
        denominator=denominator,
    )

    # The canonical beat timeline is the detected musical tactus.
    # For compound/asymmetric x/8-style meters with grouped subdivisions,
    # one detected beat represents one metric group.
    grouped_subdivisions = denominator >= 8 and any(group > 1 for group in groups)
    if grouped_subdivisions:
        timeline_beats_per_measure = len(groups)
        accent_positions = list(range(len(groups)))
    else:
        timeline_beats_per_measure = numerator
        cumulative = 0
        accent_positions = []
        for group in groups:
            accent_positions.append(cumulative)
            cumulative += int(group)

        # If no explicit grouping is musically meaningful, retain familiar
        # secondary accents without changing the number of beats in the bar.
        if groups == [1] * numerator:
            if numerator == 2:
                accent_positions = [0, 1]
            elif numerator == 4:
                accent_positions = [0, 2]
            elif numerator > 1:
                accent_positions = [0]

    accent_positions = sorted({
        int(position)
        for position in accent_positions
        if 0 <= int(position) < int(timeline_beats_per_measure)
    })
    if 0 not in accent_positions:
        accent_positions.insert(0, 0)

    return {
        "signature": f"{numerator}/{denominator}",
        "numerator": int(numerator),
        "denominator": int(denominator),
        "grouping": "+".join(str(group) for group in groups),
        "group_lengths": [int(group) for group in groups],
        "timeline_beats_per_measure": int(timeline_beats_per_measure),
        "accent_positions": accent_positions,
        "compound_or_grouped": bool(grouped_subdivisions),
    }


def _metric_signature_label(value) -> str:
    if isinstance(value, dict):
        return str(value.get("signature", "4/4") or "4/4")
    return str(value or "4/4")


def _invalidate_metric_midi(audio_hash: str) -> None:
    """Invalidate only meter-dependent MIDI artifacts."""
    midi_dir = _work_dir(audio_hash) / "midi"
    for name in (
        "chords.mid",
        "drums.mid",
        "stem_mix.mid",
        "stem_midi.json",
        "job_status.json",
        "job.log",
        "rhythm_progress.json",
        "drum_analysis.json",
    ):
        path = midi_dir / name
        if path.is_file():
            path.unlink()


def _invalidate_all_midi(audio_hash: str) -> None:
    """Force a complete MIDI regeneration, including vocal F0."""
    midi_dir = _work_dir(audio_hash) / "midi"
    for name in (
        "vocal_analysis.json",
        "vocal_progress.json",
        "vocal.mid",
        "chords.mid",
        "drums.mid",
        "stem_mix.mid",
        "stem_midi.json",
        "job_status.json",
        "job.log",
        "rhythm_progress.json",
        "drum_analysis.json",
    ):
        path = midi_dir / name
        if path.is_file():
            path.unlink()



def _measure_for_time(
    measures: list[dict[str, Any]],
    value: float,
    *,
    prefer_end: bool,
) -> int:
    if not measures:
        return 1

    t = float(value)
    for measure in measures:
        t0 = float(measure.get("time_start", 0.0) or 0.0)
        t1 = float(measure.get("time_end", t0) or t0)
        if t0 <= t < t1:
            return int(measure.get("measure", 1) or 1)

    if prefer_end and t >= float(measures[-1].get("time_end", 0.0) or 0.0):
        return int(measures[-1].get("measure", len(measures)) or len(measures))
    return int(measures[0].get("measure", 1) or 1)


def _remap_persisted_blocks_by_time(
    *,
    audio_hash: str,
    old_measures: list[dict[str, Any]],
    new_measures: list[dict[str, Any]],
) -> None:
    """Preserve edited block positions in absolute time after meter change."""
    if not old_measures or not new_measures:
        return

    blocks = _persistence.load_structure_blocks(audio_hash)
    if not blocks:
        return

    remapped = []
    previous_end = 0

    for index, block in enumerate(blocks):
        old_start = int(block.get("measure_start", 1) or 1)
        old_end = int(block.get("measure_end", old_start) or old_start)

        old_start = max(1, min(len(old_measures), old_start))
        old_end = max(old_start, min(len(old_measures), old_end))

        t0 = float(old_measures[old_start - 1].get("time_start", 0.0) or 0.0)
        t1 = float(old_measures[old_end - 1].get("time_end", t0) or t0)

        mapped_start = _measure_for_time(
            new_measures,
            t0,
            prefer_end=False,
        )
        mapped_end = _measure_for_time(
            new_measures,
            max(t0, t1 - 1e-6),
            prefer_end=True,
        )

        mapped_start = max(previous_end + 1, mapped_start)
        mapped_end = max(mapped_start, mapped_end)
        mapped_end = min(len(new_measures), mapped_end)

        updated = dict(block)
        updated["order_index"] = index
        updated["measure_start"] = int(mapped_start)
        updated["measure_end"] = int(mapped_end)
        remapped.append(updated)
        previous_end = mapped_end

        if previous_end >= len(new_measures):
            break

    if not remapped:
        return

    # Ensure the visual partition spans the whole new measure range.
    remapped[0]["measure_start"] = 1
    for index in range(1, len(remapped)):
        remapped[index]["measure_start"] = int(remapped[index - 1]["measure_end"]) + 1
        if remapped[index]["measure_start"] > len(new_measures):
            remapped = remapped[:index]
            break

    if remapped:
        remapped[-1]["measure_end"] = len(new_measures)
        _persistence._save_structure_blocks(audio_hash, remapped)

        # Any in-memory edit draft was indexed in the old meter and is invalid.
        st.session_state.pop(
            _persistence._structure_draft_key(audio_hash),
            None,
        )
        revision_key = _persistence._structure_editor_revision_key(audio_hash)
        st.session_state[revision_key] = int(
            st.session_state.get(revision_key, 0)
        ) + 1


def _motifs_from_measures(measures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    motifs = []
    patterns = [m["beat_chords"] for m in measures]
    for length in range(6, min(20, len(measures)//2) + 1):
        for i in range(0, len(measures) - (2*length) + 1):
            a = patterns[i:i+length]
            for j in range(i+length, len(measures)-length+1):
                b = patterns[j:j+length]
                total = sum(max(len(x), len(y)) for x,y in zip(a,b))
                if total <= 0: continue
                same = 0
                for x,y in zip(a,b):
                    width = max(len(x), len(y))
                    for k in range(width):
                        vx = x[k] if k < len(x) else ""
                        vy = y[k] if k < len(y) else ""
                        same += int(vx == vy and vx != "")
                sim = same / total
                if sim >= 0.72:
                    motifs.append({"a_measure_start":i+1,"a_measure_end":i+length,
                                   "b_measure_start":j+1,"b_measure_end":j+length,
                                   "length":length,"harmonic_score":round(float(sim),4)})
    motifs.sort(key=lambda item:(float(item["harmonic_score"]),int(item["length"])), reverse=True)
    selected=[]; seen=set()
    for item in motifs:
        key=(item["a_measure_start"],item["b_measure_start"])
        if key in seen: continue
        selected.append(item); seen.add(key)
        if len(selected) >= 12: break
    return selected


def _structure_from_beat_timeline(
    *,
    audio_hash: str,
    beat_timeline: list[dict[str, Any]],
    tempo: float,
    meter: dict[str, Any],
) -> dict[str, Any]:
    if len(beat_timeline) < 2:
        raise RuntimeError("Beat timeline insuffisante pour reconstruire la structure.")

    old_payload = _load_structure(audio_hash) or {}
    old_measures = list(old_payload.get("measures", []) or [])

    bpb = max(1, int(meter["timeline_beats_per_measure"]))
    measures = []

    for start in range(0, len(beat_timeline), bpb):
        stop = min(start + bpb, len(beat_timeline))
        if stop - start < max(1, bpb // 2):
            continue

        group = beat_timeline[start:stop]
        t0 = float(group[0]["time"])
        t1 = (
            float(beat_timeline[stop]["time"])
            if stop < len(beat_timeline)
            else float(group[-1]["time"]) + 60.0 / max(1.0, float(tempo))
        )
        chords = [str(item.get("chord", "N") or "N") for item in group]

        measures.append({
            "measure": len(measures) + 1,
            "time_start": t0,
            "time_end": t1,
            "beat_chords": chords,
            "pattern": " · ".join(chords),
        })

    selected = _motifs_from_measures(measures)
    speech = _load_speech(audio_hash) or {}
    words = list(speech.get("words", []) or [])
    boundaries = [1]
    for item in selected[:8]:
        boundaries.extend([
            int(item["a_measure_start"]),
            int(item["b_measure_start"]),
        ])

    blocks = _build_visual_blocks(
        boundaries=boundaries,
        measures=measures,
        words=words,
    )

    payload = {
        "tempo": float(tempo),
        "signature": str(meter["signature"]),
        "meter": dict(meter),
        # Compatibility field: this now means detected metric/tactus beats per bar.
        "beats_per_bar": int(bpb),
        "metric_beats_per_measure": int(bpb),
        "measure_count": len(measures),
        # Canonical timestamps: copied exactly, never requantized.
        "beat_timeline": beat_timeline,
        "measures": measures,
        "harmonic_motifs": selected,
        "visual_blocks": blocks,
        "visual_block_min_measures": MIN_VISUAL_BLOCK_MEASURES,
        "lyrics_source": "original",
        "timebase": "original_audio_seconds",
    }

    _structure_cache_path(audio_hash).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if old_measures:
        _remap_persisted_blocks_by_time(
            audio_hash=audio_hash,
            old_measures=old_measures,
            new_measures=measures,
        )

    return payload


def _analyze_structure(
    *,
    audio_hash: str,
    stems: dict[str, Path],
    meter: dict[str, Any],
) -> dict[str, Any]:
    """Quality-first rhythm + harmony analysis.

    Rhythm is extracted from the separated drums stem with madmom-infer.
    Harmony is extracted independently from the ORIGINAL audio with the
    lv-chordia five-network ensemble + HMM.

    Neither engine is allowed to silently fall back to the historical
    librosa/template recognizers.
    """
    drums_path = Path(stems["drums"])
    song = _song_for_hash(audio_hash)
    source = _source_path(audio_hash, song)
    if source is None or not source.is_file():
        raise RuntimeError(
            "Audio original introuvable pour l'analyse harmonique haute qualité."
        )

    rhythm = analyze_quality_beats(drums_path)
    beat_times = np.asarray(rhythm["beats"], dtype=float)
    tempo_value = float(rhythm["tempo"])

    chord_payload = analyze_chords_absolute(
        source,
        cache_path=_chord_cache_path(audio_hash),
        force=False,
    )
    chord_segments = list(chord_payload.get("segments", []) or [])
    if not chord_segments:
        raise RuntimeError("Timeline harmonique lv-chordia vide.")

    beat_timeline = []
    for i, t0 in enumerate(beat_times):
        t1 = (
            float(beat_times[i + 1])
            if i + 1 < len(beat_times)
            else float(t0) + 60.0 / max(1.0, tempo_value)
        )
        chord, raw_chord, overlap = chord_for_interval(
            chord_segments,
            float(t0),
            float(t1),
        )
        beat_timeline.append(
            {
                "index": int(i),
                "time": round(float(t0), 6),
                "strength": 0.0,
                "chord": chord,
                "chord_raw": raw_chord,
                "chord_overlap": round(float(overlap), 6),
                "rhythm_engine": str(rhythm.get("engine", "")),
                "harmony_engine": str(chord_payload.get("engine", "")),
            }
        )

    structure = _structure_from_beat_timeline(
        audio_hash=audio_hash,
        beat_timeline=beat_timeline,
        tempo=tempo_value,
        meter=meter,
    )
    structure["analysis_engines"] = {
        "stems": "bs-roformer-sw-6stems-v1",
        "rhythm": str(rhythm.get("engine", "")),
        "harmony": str(chord_payload.get("engine", "")),
        "harmony_dictionary": str(chord_payload.get("dictionary", "")),
    }
    structure["chord_segment_count"] = int(
        chord_payload.get("segment_count", len(chord_segments)) or len(chord_segments)
    )
    _structure_cache_path(audio_hash).write_text(
        json.dumps(structure, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return structure


def _load_structure(audio_hash: str) -> dict[str, Any] | None:
    path = _structure_cache_path(audio_hash)
    if not path.is_file():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    measures = list(payload.get("measures", []) or [])
    blocks = list(payload.get("visual_blocks", []) or [])
    needs_normalization = any(
        int(block.get("measure_end", 0) or 0)
        - int(block.get("measure_start", 0) or 0)
        + 1
        < MIN_VISUAL_BLOCK_MEASURES
        for block in blocks
    )

    if needs_normalization and measures:
        speech = _load_speech(audio_hash) or {}
        words = list(speech.get("words", []) or [])
        starts = [
            int(block.get("measure_start", 1) or 1)
            for block in blocks
        ]
        payload["visual_blocks"] = _build_visual_blocks(
            boundaries=starts,
            measures=measures,
            words=words,
        )
        payload["visual_block_min_measures"] = MIN_VISUAL_BLOCK_MEASURES
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return payload


@st.fragment(run_every=1.0)
def _render_midi_progress_fragment(midi_dir: Path) -> None:
    job=load_stem_midi_job(midi_dir)
    state=str(job.get("state","idle") or "idle")
    if state not in {"starting","running"}:
        st.rerun(); return
    percent=float(job.get("percent",0.0) or 0.0)
    st.progress(max(0.0,min(1.0,percent)))
    st.info(str(job.get("message") or "Génération MIDI en cours…"))
    details=[]
    if job.get("chunk_index") and job.get("chunk_total"):
        details.append(f"segment chant {job.get('chunk_index')}/{job.get('chunk_total')}")
    if job.get("elapsed_seconds") is not None:
        details.append(f"{float(job.get('elapsed_seconds')):.0f}s écoulées")
    if details: st.caption(" · ".join(details))
    with st.expander("Diagnostic MIDI en cours",expanded=False):
        st.json(job)
        vp=midi_dir/"vocal_progress.json"
        if vp.is_file():
            st.markdown("**Chant / pYIN**")
            st.json(_read_json_with_retry(vp))


def render_stem_lab_fresh_analysis(audio_hash: str) -> None:
    """EZScore analysis UI split into four workflow tabs.

    1. STEM
    2. Paroles
    3. Blocs / structure
    4. MIDI

    Tabs avoid long vertical navigation while preserving the same canonical
    timeline and dependency order.
    """
    song = _song_for_hash(audio_hash)
    source = _source_path(audio_hash, song)

    st.title("🎚️ EZScore — Analyse")
    st.caption(
        "Audio original = horloge maître · aucune erreur masquée · "
        "aucun fallback silencieux."
    )

    if source is None or not source.is_file():
        st.error("Audio original introuvable dans le répertoire EZScore.")
        return

    st.write(
        f"**Fichier :** {source.name}  \n"
        f"**Hash :** `{str(audio_hash)[:12]}`  \n"
        f"**Modèle STEM HQ :** `{DEFAULT_DEMUCS_MODEL}`"
    )

    tab_stem, tab_lyrics, tab_blocks, tab_midi = st.tabs(
        ["1 · STEM", "2 · Paroles", "3 · Blocs / structure", "4 · MIDI"]
    )

    stems = cached_stem_paths(audio_hash)
    speech = _load_speech(audio_hash)
    structure = _load_structure(audio_hash)
    words = list((speech or {}).get("words", []) or [])

    # ========================================================
    # TAB 1 — STEM
    # ========================================================
    with tab_stem:
        st.markdown("## 1 — STEM")
        st.caption("Séparation HQ BS-RoFormer-SW · 6 stems bruts, 4 stems canoniques EZScore.")

        if not demucs_available():
            st.error("BS-RoFormer-Infer n’est pas installé dans cet environnement Python.")
        elif not stems_cache_complete(audio_hash):
            if st.button(
                "Extraire les STEM HQ",
                type="primary",
                width="stretch",
                key=f"ezstem_extract_{str(audio_hash)[:12]}",
            ):
                with st.spinner("BS-RoFormer-SW sépare vocals / drums / bass / guitar / piano / other…"):
                    result = ensure_stems(
                        audio_bytes=source.read_bytes(),
                        extension=source.suffix.lower() or ".mp3",
                        audio_hash=audio_hash,
                    )
                    log = str(result.get("log_tail", "") or "")
                    if log:
                        with st.expander("Journal Demucs", expanded=False):
                            st.code(log, language="text")
                st.rerun()
            st.info("Étape 1 à lancer.")
        else:
            stems = cached_stem_paths(audio_hash)
            if len(stems) != len(STEM_NAMES):
                st.error("Cache STEM déclaré complet mais fichiers stems incomplets.")
            else:
                st.success("✓ STEM HQ prêts · BS-RoFormer-SW.")
                _download_stems(stems)

                if not _stem_ffmpeg_available():
                    st.error("FFmpeg est requis pour le lecteur STEM.")
                else:
                    st.markdown("### Lecteur STEM")
                    st.caption(
                        "Disponible dès l'étape 1. "
                        + (
                            "Paroles synchronisées actives."
                            if words
                            else "Les paroles synchronisées apparaîtront après l'étape 2."
                        )
                    )
                    _render_stem_player(
                        source,
                        stems,
                        preview_dir=_work_dir(audio_hash) / "browser_preview",
                        key=f"ezstem_player_{str(audio_hash)[:12]}_{len(words)}",
                        words=words,
                    )

    # ========================================================
    # TAB 2 — PAROLES
    # ========================================================
    with tab_lyrics:
        st.markdown("## 2 — Paroles")
        st.caption(
            "Whisper small sur l'audio original. "
            "Après analyse, le lecteur STEM de l'onglet 1 défile les paroles synchronisées."
        )

        if not stems_cache_complete(audio_hash):
            st.info("Terminer d'abord l'étape 1 — STEM.")
        elif speech is None:
            if st.button(
                "Analyser les paroles",
                type="primary",
                width="stretch",
                key=f"ezstem_speech_{str(audio_hash)[:12]}",
            ):
                with st.spinner("Whisper small analyse l'audio original…"):
                    _transcribe_original(source, audio_hash)
                st.rerun()
            st.info("Étape 2 à lancer.")
        else:
            st.success(
                f"✓ Paroles prêtes · {len(words)} mots horodatés · "
                f"langue `{speech.get('language', 'auto')}`."
            )
            tab_text, tab_words = st.tabs(["Paroles + accords", "Mots horodatés"])
            with tab_text:
                render_chords_lyrics_editor(
                    stem_module=__import__(
                        "ezscore.ui.stem_lab_analysis",
                        fromlist=["*"],
                    ),
                    audio_hash=audio_hash,
                )
            with tab_words:
                st.dataframe(
                    [
                        {
                            "Début": round(float(w.get("start", 0.0)), 3),
                            "Fin": round(float(w.get("end", 0.0)), 3),
                            "Mot": str(w.get("text", "") or ""),
                        }
                        for w in words
                    ],
                    hide_index=True,
                    width="stretch",
                )

    # ========================================================
    # TAB 3 — BLOCS / STRUCTURE
    # ========================================================
    with tab_blocks:
        st.markdown("## 3 — Blocs / structure")
        st.caption(
            "La signature regroupe les beats en mesures et détermine les temps "
            "forts/faibles. Les timestamps audio des beats restent inchangés."
        )
        if not quality_rhythm_engine_available():
            st.error("Analyse rythmique HQ indisponible : paquet `madmom-infer` absent.")
        if not quality_chord_engine_available():
            st.error("Analyse harmonique HQ indisponible : paquet `lv-chordia` absent.")

        if not stems_cache_complete(audio_hash):
            st.info("Terminer d'abord l'étape 1 — STEM.")
        elif speech is None:
            st.info("Terminer d'abord l'étape 2 — Paroles.")
        else:
            current_signature = str(
                (structure or {}).get("signature", "4/4") or "4/4"
            )
            current_meter = dict((structure or {}).get("meter", {}) or {})
            current_grouping = str(
                current_meter.get("grouping", "") or ""
            )

            signature_key = f"ezstem_signature_{str(audio_hash)[:12]}"
            grouping_key = f"ezstem_grouping_{str(audio_hash)[:12]}"

            if signature_key not in st.session_state:
                st.session_state[signature_key] = current_signature
            if grouping_key not in st.session_state:
                st.session_state[grouping_key] = current_grouping

            meter_col1, meter_col2 = st.columns([1, 1.35])
            with meter_col1:
                selected_signature = st.text_input(
                    "Signature",
                    key=signature_key,
                    help=(
                        "Format libre N/D : 2/4, 3/4, 4/4, 5/4, 7/4, "
                        "5/8, 6/8, 7/8, 9/8, 12/8, etc."
                    ),
                )
            with meter_col2:
                selected_grouping = st.text_input(
                    "Groupement métrique",
                    key=grouping_key,
                    placeholder="Auto",
                    help=(
                        "Optionnel. Exemples : 3+3 pour 6/8, 3+3+3 pour 9/8, "
                        "3+2 pour 5/4, 4+3 pour 7/4, 2+2+3 pour 7/8."
                    ),
                )

            meter_error = None
            selected_meter = None
            try:
                selected_meter = _meter_spec(
                    selected_signature,
                    selected_grouping,
                )
            except ValueError as exc:
                meter_error = str(exc)
                st.error(meter_error)

            if selected_meter is not None:
                st.caption(
                    f"{selected_meter['signature']} · "
                    f"{selected_meter['timeline_beats_per_measure']} temps métriques/mesure · "
                    f"groupement {selected_meter['grouping']} · "
                    "timeline audio inchangée."
                )

            if structure is None:
                if st.button(
                    "Détecter les blocs / structure",
                    type="primary",
                    width="stretch",
                    key=f"ezstem_structure_{str(audio_hash)[:12]}",
                    disabled=(selected_meter is None or not quality_rhythm_engine_available() or not quality_chord_engine_available()),
                ):
                    with st.spinner("Analyse beats + accords + répétitions + blocs…"):
                        _analyze_structure(
                            audio_hash=audio_hash,
                            stems=cached_stem_paths(audio_hash),
                            meter=dict(selected_meter),
                        )
                        _invalidate_metric_midi(audio_hash)
                    st.rerun()
                st.info("Étape 3 à lancer.")
            else:
                has_beat_timeline = bool(structure.get("beat_timeline"))
                if not has_beat_timeline:
                    st.warning(
                        "Cache structure ancien : un recalcul complet est requis "
                        "une seule fois pour persister la timeline des beats."
                    )

                signature_changed = bool(selected_meter) and (str(selected_meter.get('signature')) != current_signature or str(selected_meter.get('grouping')) != current_grouping)
                recalc_label = (
                    f"Recalculer en {selected_meter['signature']}"
                    if signature_changed
                    else "Recalculer les blocs / structure"
                )

                if st.button(
                    recalc_label,
                    type="primary" if signature_changed else "secondary",
                    width="stretch",
                    key=f"ezstem_structure_recalc_{str(audio_hash)[:12]}",
                    disabled=(selected_meter is None or not quality_rhythm_engine_available() or not quality_chord_engine_available()),
                ):
                    if has_beat_timeline:
                        with st.spinner("Reconstruction métrique + blocs…"):
                            _structure_from_beat_timeline(
                                audio_hash=audio_hash,
                                beat_timeline=list(structure["beat_timeline"]),
                                tempo=float(structure.get("tempo", 120.0) or 120.0),
                                meter=dict(selected_meter),
                            )
                            _invalidate_metric_midi(audio_hash)
                    else:
                        with st.spinner(
                            "Extraction de la timeline beats puis reconstruction…"
                        ):
                            _analyze_structure(
                                audio_hash=audio_hash,
                                stems=cached_stem_paths(audio_hash),
                                meter=dict(selected_meter),
                            )
                            _invalidate_metric_midi(audio_hash)
                    st.rerun()

                blocks = list(structure.get("visual_blocks", []) or [])
                st.success(
                    f"✓ {current_signature} · "
                    f"{len(blocks)} blocs · "
                    f"{int(structure.get('measure_count', 0))} mesures · "
                    f"tempo ≈ {float(structure.get('tempo', 0.0)):.1f} BPM."
                )

                for block in blocks:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(
                                f"### Bloc {block.get('cluster', '?')} · "
                                f"mesures {block.get('measure_start', 0)}–"
                                f"{block.get('measure_end', 0)} · "
                                f"{int(block.get('measure_end', 0)) - int(block.get('measure_start', 0)) + 1} mesures"
                            )
                        with c2:
                            st.caption(
                                f"{float(block.get('time_start', 0.0)):.1f}s → "
                                f"{float(block.get('time_end', 0.0)):.1f}s"
                            )
                        lyrics = str(block.get("lyrics", "") or "").strip()
                        if lyrics:
                            st.markdown(
                                "<div style='margin-top:.65rem;padding:.75rem 1rem;"
                                "border-left:4px solid #2f80ed;"
                                "font-size:1.08rem;line-height:1.55;'>"
                                + lyrics
                                + "</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("Section instrumentale / aucune parole détectée.")

                with st.expander("Progressions harmoniques / mesures", expanded=False):
                    st.dataframe(
                        [
                            {
                                "Mesure": m.get("measure"),
                                "Début": round(float(m.get("time_start", 0.0)), 2),
                                "Fin": round(float(m.get("time_end", 0.0)), 2),
                                "Accords / temps": " · ".join(m.get("beat_chords", [])),
                            }
                            for m in list(structure.get("measures", []) or [])
                        ],
                        hide_index=True,
                        width="stretch",
                    )

    # ========================================================
    # TAB 4 — MIDI
    # ========================================================
    with tab_midi:
        st.markdown("## 4 — MIDI")
        st.caption(
            "Accords + Batterie proviennent directement de la timeline métrique "
            "de l'étape 3. Le chant F0 est réutilisé s'il existe."
        )

        structure = _load_structure(audio_hash)
        if structure is None:
            st.info("Terminer d'abord l'étape 3 — Blocs / structure.")
        else:
            midi_dir = _work_dir(audio_hash) / "midi"
            structure_path = _structure_cache_path(audio_hash)
            meta_path = midi_dir / "stem_midi.json"
            job = load_stem_midi_job(midi_dir)
            job_state = str(job.get("state", "idle") or "idle")

            if job_state in {"starting", "running"}:
                _render_midi_progress_fragment(midi_dir)

            elif job_state == "error":
                st.error(
                    "Génération MIDI arrêtée sur erreur : "
                    + str(job.get("message", ""))
                )

                retry_metric_col, retry_all_col = st.columns(2)
                with retry_metric_col:
                    if st.button(
                        "↻ Réessayer métrique",
                        width="stretch",
                        key=f"ezstem_midi_retry_metric_{str(audio_hash)[:12]}",
                    ):
                        _invalidate_metric_midi(audio_hash)
                        stems_now = cached_stem_paths(audio_hash)
                        launch_stem_midi_job(
                            vocals_path=stems_now["vocals"],
                            drums_path=stems_now["drums"],
                            structure_path=structure_path,
                            output_dir=midi_dir,
                        )
                        st.rerun()

                with retry_all_col:
                    if st.button(
                        "↻ Réessayer tout le MIDI",
                        type="primary",
                        width="stretch",
                        key=f"ezstem_midi_retry_all_{str(audio_hash)[:12]}",
                    ):
                        _invalidate_all_midi(audio_hash)
                        stems_now = cached_stem_paths(audio_hash)
                        launch_stem_midi_job(
                            vocals_path=stems_now["vocals"],
                            drums_path=stems_now["drums"],
                            structure_path=structure_path,
                            output_dir=midi_dir,
                        )
                        st.rerun()

                with st.expander("Diagnostic complet", expanded=True):
                    st.json(job)
                    st.code(str(job.get("traceback", "") or ""), language="text")
                    log_path = midi_dir / "job.log"
                    if log_path.is_file():
                        st.code(
                            log_path.read_text(encoding="utf-8", errors="replace"),
                            language="text",
                        )

            else:
                midi_meta = None
                if meta_path.is_file():
                    midi_meta = _read_json_with_retry(meta_path)

                midi_complete = bool(
                    midi_meta
                    and str(midi_meta.get("state", "complete") or "complete") == "complete"
                    and set(
                        midi_meta.get(
                            "available_tracks",
                            ["vocal", "chords", "drums"],
                        )
                    ) >= {"vocal", "chords", "drums"}
                    and (midi_dir / "vocal.mid").is_file()
                    and (midi_dir / "chords.mid").is_file()
                    and (midi_dir / "drums.mid").is_file()
                )

                if not midi_complete:
                    if st.button(
                        "Générer les 3 pistes MIDI",
                        type="primary",
                        width="stretch",
                        key=f"ezstem_midi_generate_{str(audio_hash)[:12]}",
                    ):
                        stems_now = cached_stem_paths(audio_hash)
                        launch_stem_midi_job(
                            vocals_path=stems_now["vocals"],
                            drums_path=stems_now["drums"],
                            structure_path=structure_path,
                            output_dir=midi_dir,
                        )
                        st.rerun()
                    st.info("Étape 4 à lancer.")
                else:
                    st.success(
                        "✓ MIDI prêts · "
                        f"{int(midi_meta.get('vocal_note_count', 0))} notes chant · "
                        f"{int(midi_meta.get('drum_beat_count', 0))} beats batterie."
                    )

                    st.markdown("### Régénération")
                    st.caption(
                        "Métrique = Accords + Batterie + combiné. "
                        "Complète = réanalyse aussi le chant F0 et recrée vocal.mid."
                    )
                    regen_metric_col, regen_all_col = st.columns(2)

                    with regen_metric_col:
                        if st.button(
                            "↻ Régénérer métrique",
                            width="stretch",
                            key=f"ezstem_midi_regen_metric_{str(audio_hash)[:12]}",
                        ):
                            _invalidate_metric_midi(audio_hash)
                            stems_now = cached_stem_paths(audio_hash)
                            launch_stem_midi_job(
                                vocals_path=stems_now["vocals"],
                                drums_path=stems_now["drums"],
                                structure_path=structure_path,
                                output_dir=midi_dir,
                            )
                            st.rerun()

                    with regen_all_col:
                        if st.button(
                            "↻ Régénérer tout le MIDI",
                            type="primary",
                            width="stretch",
                            key=f"ezstem_midi_regen_all_{str(audio_hash)[:12]}",
                        ):
                            _invalidate_all_midi(audio_hash)
                            stems_now = cached_stem_paths(audio_hash)
                            launch_stem_midi_job(
                                vocals_path=stems_now["vocals"],
                                drums_path=stems_now["drums"],
                                structure_path=structure_path,
                                output_dir=midi_dir,
                            )
                            st.rerun()

                    cols = st.columns(4)
                    for col, (label, filename, key_name) in zip(
                        cols,
                        [
                            ("Chant", "vocal.mid", "vocal"),
                            ("Accords", "chords.mid", "chords"),
                            ("Batterie", "drums.mid", "drums"),
                            ("Combiné", "stem_mix.mid", "combined"),
                        ],
                    ):
                        path = midi_dir / filename
                        with col:
                            st.download_button(
                                f"⬇ MIDI {label}",
                                data=path.read_bytes(),
                                file_name=filename,
                                mime="audio/midi",
                                width="stretch",
                                key=f"ezstem_midi_dl_{key_name}_{str(audio_hash)[:12]}",
                            )

                    st.markdown("### Lecteur Audio + MIDI")
                    st.caption(
                        "Audio original = horloge maître · MIDI Chant / Accords / "
                        "Batterie synchronisés · instruments modifiables en temps réel."
                    )
                    preview_path = _make_browser_preview(
                        source,
                        _work_dir(audio_hash) / "browser_preview",
                    )
                    render_stem_midi_sync_player(
                        audio_path=preview_path,
                        midi_metadata=midi_meta,
                        key=f"ezstem_midi_sync_{str(audio_hash)[:12]}",
                    )

