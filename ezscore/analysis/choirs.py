"""Dedicated canonical choir/backing-vocal analyzer for EZScore.

V4 keeps the validated Whisper-small choir transcription, then classifies every
candidate against BOTH isolated vocal stems:

    lead_vocals.wav
    backing_vocals.wav

Goal:
- keep true backing-only words;
- keep true lead+backing doublings;
- reject lead leakage misread as choir.

The validated lead transcript is never modified. Chord analysis is untouched.
No title/artist/timestamp special case exists here.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import librosa
import numpy as np
import torch
import whisper

from ezscore.analysis.vocal_stems import vocal_stem_paths


APP_DIR = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = APP_DIR / "data" / "analysis" / "stem_lab"

# Rollback reference:
# GitHub restore/full-reanalysis-r1 @
# 9fedde9557e6ed9100ba29caaebcfcce848ef493
# choir engine: ezscore-choir-whisper-small-v3 / schema 3
CHOIR_SCHEMA_VERSION = 5
CHOIR_ENGINE = "ezscore-choir-whisper-small-v4.2"
CHOIR_CLASSIFIER = "lead-backing-acoustic-v2"
DEFAULT_WHISPER_MODEL = "small"

TARGET_SAMPLE_RATE = 16000
FRAME_LENGTH = 1024
HOP_LENGTH = 160
SPLIT_TOP_DB = 38.0
MIN_ACTIVE_SECONDS = 0.20
MERGE_GAP_SECONDS = 0.85
CHUNK_PADDING_SECONDS = 0.35
MAX_CHUNK_SECONDS = 28.0

MIN_WORD_PROBABILITY = 0.25
MAX_NO_SPEECH_PROBABILITY = 0.72
MIN_SEGMENT_AVG_LOGPROB = -1.45

# Generic lead/backing discrimination.
# These values are signal-domain thresholds, never song-specific.
CLASSIFY_PAD_SECONDS = 0.10
LEAD_MATCH_PAD_SECONDS = 0.16
MIN_TEMPORAL_OVERLAP = 0.18
MIN_DOUBLING_BACKING_SHARE = 0.12
STRONG_DOUBLING_BACKING_SHARE = 0.25
MIN_DISTINCT_BACKING_SHARE = 0.12
DISTINCT_SPECTRAL_SIMILARITY = 0.78

# V4.2: independent-signal evidence.
MIN_RECOVERABLE_BACKING_SHARE = 0.06
MAX_INDEPENDENT_CORRELATION = 0.55
MIN_INDEPENDENT_RESIDUAL_RATIO = 0.62
MIN_INDEPENDENT_BACKING_ACTIVITY = 0.45


class ChoirAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class TimeRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, float(self.end) - float(self.start))


@dataclass(frozen=True)
class VocalSignal:
    y: np.ndarray
    sr: int
    rms_reference: float


def _clean_hash(audio_hash: str) -> str:
    value = "".join(
        ch
        for ch in str(audio_hash or "").lower()
        if ch in "0123456789abcdef"
    )
    if not value:
        raise ValueError("audio_hash vide/invalide")
    return value


def choir_analysis_path(audio_hash: str) -> Path:
    return ANALYSIS_ROOT / _clean_hash(audio_hash) / "choir_analysis.json"


def lead_transcript_path(audio_hash: str) -> Path:
    return ANALYSIS_ROOT / _clean_hash(audio_hash) / "whisper_original_small.json"


def load_choir_analysis(audio_hash: str) -> dict[str, Any] | None:
    path = choir_analysis_path(audio_hash)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if int(payload.get("schema_version", 0) or 0) != CHOIR_SCHEMA_VERSION:
        return None
    if str(payload.get("engine", "") or "") != CHOIR_ENGINE:
        return None
    return payload


def _source_signature(path: Path) -> dict[str, int | str]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def choir_analysis_is_current(audio_hash: str) -> bool:
    payload = load_choir_analysis(audio_hash)
    if payload is None:
        return False

    backing = Path(str(payload.get("source", "") or ""))
    lead_audio = Path(str(payload.get("lead_source", "") or ""))
    lead_text = lead_transcript_path(audio_hash)

    if (
        not backing.is_file()
        or not lead_audio.is_file()
        or not lead_text.is_file()
    ):
        return False

    return (
        dict(payload.get("backing_signature", {}) or {})
        == _source_signature(backing)
        and dict(payload.get("lead_audio_signature", {}) or {})
        == _source_signature(lead_audio)
        and dict(payload.get("lead_signature", {}) or {})
        == _source_signature(lead_text)
    )


def delete_choir_analysis(audio_hash: str) -> None:
    try:
        choir_analysis_path(audio_hash).unlink()
    except FileNotFoundError:
        pass


def _load_master_transcript(
    audio_hash: str,
) -> tuple[str, Path, list[dict[str, Any]]]:
    path = lead_transcript_path(audio_hash)
    if not path.is_file():
        raise ChoirAnalysisError(
            "Analyse Chant principale absente : "
            "whisper_original_small.json requis."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    language = str(payload.get("language", "") or "").strip().lower()
    if not language:
        raise ChoirAnalysisError(
            "Langue Chant principale absente : "
            "impossible d'analyser les Chœurs."
        )

    words: list[dict[str, Any]] = []
    for item in list(payload.get("words", []) or []):
        text = str(item.get("text", "") or "").strip()
        start = float(item.get("start", 0.0) or 0.0)
        end = float(item.get("end", start) or start)
        if text and end > start:
            words.append(
                {
                    "text": text,
                    "start": start,
                    "end": end,
                }
            )

    return language, path, words


def _merge_ranges(
    ranges: Iterable[TimeRange],
    *,
    max_gap: float = MERGE_GAP_SECONDS,
) -> list[TimeRange]:
    ordered = sorted(ranges, key=lambda item: (item.start, item.end))
    if not ordered:
        return []

    merged = [ordered[0]]
    for item in ordered[1:]:
        previous = merged[-1]
        if float(item.start) - float(previous.end) <= float(max_gap):
            merged[-1] = TimeRange(
                start=float(previous.start),
                end=max(float(previous.end), float(item.end)),
            )
        else:
            merged.append(item)
    return merged


def _split_long_range(item: TimeRange) -> list[TimeRange]:
    if item.duration <= MAX_CHUNK_SECONDS:
        return [item]

    chunks: list[TimeRange] = []
    cursor = float(item.start)
    while cursor < float(item.end):
        end = min(float(item.end), cursor + MAX_CHUNK_SECONDS)
        chunks.append(TimeRange(cursor, end))
        cursor = end
    return chunks


def _load_signal(path: Path) -> VocalSignal:
    y, sr = librosa.load(
        str(path),
        sr=TARGET_SAMPLE_RATE,
        mono=True,
    )
    y = np.asarray(y, dtype=np.float32)
    if y.size == 0:
        raise ChoirAnalysisError(f"Signal vocal vide : {path}")

    rms = np.asarray(
        librosa.feature.rms(
            y=y,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH,
        )[0],
        dtype=float,
    )
    positive = rms[rms > 1e-9]
    reference = (
        float(np.percentile(positive, 75))
        if positive.size
        else 1e-9
    )
    return VocalSignal(
        y=y,
        sr=int(sr),
        rms_reference=max(reference, 1e-9),
    )


def detect_vocal_activity(
    backing_path: Path,
) -> tuple[VocalSignal, list[TimeRange], dict[str, float]]:
    path = Path(backing_path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise ChoirAnalysisError(f"Stem Chœurs invalide : {path}")

    signal = _load_signal(path)
    y = signal.y
    sr = signal.sr
    duration = float(y.size) / float(sr)

    intervals = librosa.effects.split(
        y,
        top_db=SPLIT_TOP_DB,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH,
    )

    raw: list[TimeRange] = []
    for start_sample, end_sample in intervals:
        item = TimeRange(
            float(start_sample) / float(sr),
            float(end_sample) / float(sr),
        )
        if item.duration >= MIN_ACTIVE_SECONDS:
            raw.append(item)

    merged = _merge_ranges(raw)
    chunks: list[TimeRange] = []
    for item in merged:
        chunks.extend(_split_long_range(item))

    rms = np.asarray(
        librosa.feature.rms(
            y=y,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH,
        )[0],
        dtype=float,
    )
    positive = rms[rms > 1e-9]
    active_seconds = float(sum(item.duration for item in merged))

    diagnostics = {
        "duration_seconds": duration,
        "active_seconds": active_seconds,
        "active_ratio": (
            active_seconds / duration
            if duration > 0.0
            else 0.0
        ),
        "rms_median": (
            float(np.median(positive))
            if positive.size
            else 0.0
        ),
        "rms_p75": (
            float(np.percentile(positive, 75))
            if positive.size
            else 0.0
        ),
        "rms_p95": (
            float(np.percentile(positive, 95))
            if positive.size
            else 0.0
        ),
    }
    return signal, chunks, diagnostics


@lru_cache(maxsize=2)
def _whisper_model(model_name: str, device: str):
    return whisper.load_model(str(model_name), device=str(device))


def _deduplicate_words(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(
        words,
        key=lambda item: (
            float(item.get("start", 0.0) or 0.0),
            float(item.get("end", 0.0) or 0.0),
            str(item.get("text", "") or "").casefold(),
        ),
    )
    result: list[dict[str, Any]] = []

    for word in ordered:
        text = str(word.get("text", "") or "").strip()
        if not text:
            continue

        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        duplicate = False

        for previous in reversed(result[-4:]):
            if (
                str(previous.get("text", "")).casefold()
                != text.casefold()
            ):
                continue

            p0 = float(previous.get("start", 0.0) or 0.0)
            p1 = float(previous.get("end", p0) or p0)
            overlap = max(
                0.0,
                min(end, p1) - max(start, p0),
            )
            shorter = max(
                0.001,
                min(end - start, p1 - p0),
            )
            if overlap / shorter >= 0.70:
                duplicate = True
                if (
                    float(word.get("confidence", 0.0) or 0.0)
                    > float(previous.get("confidence", 0.0) or 0.0)
                ):
                    previous.update(word)
                break

        if not duplicate:
            result.append(dict(word))

    return result


def _chunk_signal(
    y: np.ndarray,
    sr: int,
    item: TimeRange,
) -> tuple[np.ndarray, float]:
    duration = float(y.size) / float(sr)
    start = max(
        0.0,
        float(item.start) - CHUNK_PADDING_SECONDS,
    )
    end = min(
        duration,
        float(item.end) + CHUNK_PADDING_SECONDS,
    )
    i0 = max(0, int(round(start * sr)))
    i1 = min(y.size, int(round(end * sr)))
    return np.asarray(y[i0:i1], dtype=np.float32), start


def _window(
    signal: VocalSignal,
    start: float,
    end: float,
) -> np.ndarray:
    t0 = max(0.0, float(start) - CLASSIFY_PAD_SECONDS)
    t1 = max(t0 + 0.04, float(end) + CLASSIFY_PAD_SECONDS)
    i0 = max(0, int(round(t0 * signal.sr)))
    i1 = min(signal.y.size, int(round(t1 * signal.sr)))
    if i1 <= i0:
        return np.zeros(0, dtype=np.float32)
    return np.asarray(signal.y[i0:i1], dtype=np.float32)


def _local_rms(
    signal: VocalSignal,
    start: float,
    end: float,
) -> tuple[float, float]:
    chunk = _window(signal, start, end)
    if chunk.size == 0:
        return 0.0, 0.0

    raw = float(np.sqrt(np.mean(np.square(chunk), dtype=np.float64)))
    normalized = raw / max(signal.rms_reference, 1e-9)
    return raw, float(normalized)


def _spectral_similarity(
    lead_signal: VocalSignal,
    backing_signal: VocalSignal,
    start: float,
    end: float,
) -> float:
    lead_chunk = _window(lead_signal, start, end)
    backing_chunk = _window(backing_signal, start, end)

    length = min(lead_chunk.size, backing_chunk.size)
    if length < 640:
        return 0.0

    lead_chunk = lead_chunk[:length]
    backing_chunk = backing_chunk[:length]

    lead_spec = np.abs(
        librosa.stft(
            lead_chunk,
            n_fft=512,
            hop_length=160,
            win_length=512,
            center=True,
        )
    )
    backing_spec = np.abs(
        librosa.stft(
            backing_chunk,
            n_fft=512,
            hop_length=160,
            win_length=512,
            center=True,
        )
    )

    if not lead_spec.size or not backing_spec.size:
        return 0.0

    lead_profile = np.mean(np.log1p(lead_spec), axis=1)
    backing_profile = np.mean(np.log1p(backing_spec), axis=1)

    denominator = (
        float(np.linalg.norm(lead_profile))
        * float(np.linalg.norm(backing_profile))
    )
    if denominator <= 1e-12:
        return 0.0

    value = float(
        np.dot(lead_profile, backing_profile) / denominator
    )
    return float(max(0.0, min(1.0, value)))


def _waveform_independence(
    lead_signal: VocalSignal,
    backing_signal: VocalSignal,
    start: float,
    end: float,
) -> tuple[float, float]:
    lead_chunk = _window(lead_signal, start, end)
    backing_chunk = _window(backing_signal, start, end)

    length = min(lead_chunk.size, backing_chunk.size)
    if length < 640:
        return 0.0, 0.0

    lead = np.asarray(lead_chunk[:length], dtype=np.float64)
    backing = np.asarray(backing_chunk[:length], dtype=np.float64)

    lead -= float(np.mean(lead))
    backing -= float(np.mean(backing))

    lead_norm = float(np.linalg.norm(lead))
    backing_norm = float(np.linalg.norm(backing))
    if lead_norm <= 1e-12 or backing_norm <= 1e-12:
        return 0.0, 0.0

    correlation = float(
        np.dot(lead, backing) / (lead_norm * backing_norm)
    )
    abs_correlation = float(
        max(0.0, min(1.0, abs(correlation)))
    )

    lead_power = float(np.dot(lead, lead))
    if lead_power <= 1e-12:
        return abs_correlation, 1.0

    scale = float(np.dot(backing, lead) / lead_power)
    residual = backing - (scale * lead)

    residual_rms = float(
        np.sqrt(np.mean(np.square(residual), dtype=np.float64))
    )
    backing_rms = float(
        np.sqrt(np.mean(np.square(backing), dtype=np.float64))
    )
    residual_ratio = (
        residual_rms / backing_rms
        if backing_rms > 1e-12
        else 0.0
    )

    return (
        abs_correlation,
        float(max(0.0, min(1.0, residual_ratio))),
    )


def _lead_overlap(
    candidate: dict[str, Any],
    lead_words: list[dict[str, Any]],
) -> tuple[float, dict[str, Any] | None]:
    start = float(candidate.get("start", 0.0) or 0.0)
    end = float(candidate.get("end", start) or start)
    duration = max(0.001, end - start)

    best_ratio = 0.0
    best_word = None

    for lead in lead_words:
        lead_start = (
            float(lead.get("start", 0.0) or 0.0)
            - LEAD_MATCH_PAD_SECONDS
        )
        lead_end = (
            float(lead.get("end", lead_start) or lead_start)
            + LEAD_MATCH_PAD_SECONDS
        )

        overlap = max(
            0.0,
            min(end, lead_end) - max(start, lead_start),
        )
        ratio = overlap / duration
        if ratio > best_ratio:
            best_ratio = ratio
            best_word = lead

    return float(max(0.0, min(1.0, best_ratio))), best_word


def _classify_candidate(
    word: dict[str, Any],
    *,
    lead_words: list[dict[str, Any]],
    lead_signal: VocalSignal,
    backing_signal: VocalSignal,
) -> tuple[bool, dict[str, Any]]:
    start = float(word.get("start", 0.0) or 0.0)
    end = float(word.get("end", start) or start)

    overlap_ratio, matched_lead = _lead_overlap(
        word,
        lead_words,
    )

    lead_rms, lead_activity = _local_rms(
        lead_signal,
        start,
        end,
    )
    backing_rms, backing_activity = _local_rms(
        backing_signal,
        start,
        end,
    )

    total_raw = lead_rms + backing_rms
    backing_share = (
        backing_rms / total_raw
        if total_raw > 1e-12
        else 0.0
    )

    similarity = _spectral_similarity(
        lead_signal,
        backing_signal,
        start,
        end,
    )
    waveform_correlation, residual_ratio = _waveform_independence(
        lead_signal,
        backing_signal,
        start,
        end,
    )

    lead_overlap = overlap_ratio >= MIN_TEMPORAL_OVERLAP

    if not lead_overlap:
        classification = "backing_only"
        keep = True

    # Preserve V4.1 anti-hallucination behaviour for near-zero backing energy.
    elif backing_share < MIN_RECOVERABLE_BACKING_SHARE:
        classification = "lead_leakage"
        keep = False

    # Recover quiet simultaneous backing only when it is acoustically
    # independent from the lead, rather than a scaled copy of it.
    elif backing_share < MIN_DOUBLING_BACKING_SHARE:
        independent = (
            waveform_correlation <= MAX_INDEPENDENT_CORRELATION
            and residual_ratio >= MIN_INDEPENDENT_RESIDUAL_RATIO
            and backing_activity >= MIN_INDEPENDENT_BACKING_ACTIVITY
        )
        if independent:
            classification = "backing_independent_weak"
            keep = True
        else:
            classification = "lead_leakage"
            keep = False

    elif backing_share >= STRONG_DOUBLING_BACKING_SHARE:
        classification = "doubling"
        keep = True

    elif (
        backing_share >= MIN_DISTINCT_BACKING_SHARE
        and similarity < DISTINCT_SPECTRAL_SIMILARITY
        and backing_activity >= 0.40
    ):
        classification = "backing_distinct"
        keep = True

    else:
        classification = "doubling_weak"
        keep = True

    diagnostics = {
        "classification": classification,
        "lead_overlap_ratio": round(overlap_ratio, 6),
        "matched_lead_text": (
            str(matched_lead.get("text", "") or "")
            if matched_lead is not None
            else ""
        ),
        "lead_rms": round(lead_rms, 8),
        "backing_rms": round(backing_rms, 8),
        "lead_activity": round(lead_activity, 6),
        "backing_activity": round(backing_activity, 6),
        "backing_share": round(backing_share, 6),
        "spectral_similarity": round(similarity, 6),
        "waveform_correlation": round(waveform_correlation, 6),
        "residual_ratio": round(residual_ratio, 6),
    }
    return bool(keep), diagnostics


def analyze_choirs(
    *,
    audio_hash: str,
    backing_path: Path | None = None,
    force: bool = False,
    model_name: str = DEFAULT_WHISPER_MODEL,
    device: str | None = None,
) -> dict[str, Any]:
    clean_hash = _clean_hash(audio_hash)

    if not force and choir_analysis_is_current(clean_hash):
        cached = load_choir_analysis(clean_hash)
        if cached is not None:
            return cached

    vocal_paths = vocal_stem_paths(clean_hash)

    if backing_path is None:
        backing_path = vocal_paths.get("backing_vocals")

    lead_audio_path = vocal_paths.get("lead_vocals")

    if backing_path is None:
        raise ChoirAnalysisError(
            "backing_vocals.wav absent : "
            "exécuter d'abord la séparation Chant / Chœurs."
        )
    if lead_audio_path is None:
        raise ChoirAnalysisError(
            "lead_vocals.wav absent : "
            "classification Chant / Chœurs impossible."
        )

    backing = Path(backing_path)
    lead_audio = Path(lead_audio_path)

    if not backing.is_file():
        raise ChoirAnalysisError(
            f"backing_vocals.wav introuvable : {backing}"
        )
    if not lead_audio.is_file():
        raise ChoirAnalysisError(
            f"lead_vocals.wav introuvable : {lead_audio}"
        )

    language, lead_path, lead_words = _load_master_transcript(
        clean_hash
    )

    backing_signal, chunks, diagnostics = detect_vocal_activity(
        backing
    )
    lead_signal = _load_signal(lead_audio)

    selected_device = str(
        device or ("cuda" if torch.cuda.is_available() else "cpu")
    )
    model = _whisper_model(str(model_name), selected_device)

    raw_words: list[dict[str, Any]] = []
    phrases: list[dict[str, Any]] = []

    for index, active in enumerate(chunks):
        audio_chunk, chunk_start = _chunk_signal(
            backing_signal.y,
            backing_signal.sr,
            active,
        )
        if audio_chunk.size == 0:
            continue

        result = model.transcribe(
            audio_chunk,
            language=language,
            word_timestamps=True,
            fp16=selected_device.startswith("cuda"),
            verbose=False,
            condition_on_previous_text=False,
            temperature=0.0,
            initial_prompt=(
                "Transcribe only the audible backing vocals exactly. "
                "Preserve repeated sung syllables and vocalisations such as "
                "la, na, oh, ah and ooh when they are actually audible. "
                "Do not invent lyrics for silence or instruments."
            ),
        )

        accepted = 0
        raw_text = str(result.get("text", "") or "").strip()

        for segment in result.get("segments", []) or []:
            no_speech = float(
                segment.get("no_speech_prob", 0.0) or 0.0
            )
            avg_logprob = float(
                segment.get("avg_logprob", 0.0) or 0.0
            )
            if no_speech > MAX_NO_SPEECH_PROBABILITY:
                continue
            if avg_logprob < MIN_SEGMENT_AVG_LOGPROB:
                continue

            for raw_word in segment.get("words", []) or []:
                text = str(
                    raw_word.get("word", "") or ""
                ).strip()
                local_start = float(
                    raw_word.get("start", 0.0) or 0.0
                )
                local_end = float(
                    raw_word.get("end", local_start) or local_start
                )
                confidence = float(
                    raw_word.get("probability", 0.0) or 0.0
                )

                if not text or local_end <= local_start:
                    continue
                if confidence < MIN_WORD_PROBABILITY:
                    continue

                start = chunk_start + local_start
                end = chunk_start + local_end
                center = (start + end) / 2.0

                if not (
                    float(active.start)
                    <= center
                    <= float(active.end)
                ):
                    continue

                raw_words.append(
                    {
                        "start": round(start, 6),
                        "end": round(end, 6),
                        "text": text,
                        "confidence": round(confidence, 6),
                        "type": "word",
                        "phrase_index": index,
                    }
                )
                accepted += 1

        phrases.append(
            {
                "index": index,
                "start": round(float(active.start), 6),
                "end": round(float(active.end), 6),
                "duration": round(float(active.duration), 6),
                "raw_text": raw_text,
                "accepted_word_count": int(accepted),
                "transcribed": bool(accepted),
            }
        )

    raw_words = _deduplicate_words(raw_words)

    words: list[dict[str, Any]] = []
    rejected_words: list[dict[str, Any]] = []
    classification_counts: dict[str, int] = {}

    for word in raw_words:
        keep, evidence = _classify_candidate(
            word,
            lead_words=lead_words,
            lead_signal=lead_signal,
            backing_signal=backing_signal,
        )

        classification = str(
            evidence.get("classification", "unknown")
        )
        classification_counts[classification] = (
            classification_counts.get(classification, 0) + 1
        )

        enriched = dict(word)
        enriched["source_class"] = classification
        enriched["source_evidence"] = evidence

        if keep:
            words.append(enriched)
        else:
            enriched["reject_reason"] = "lead_leakage"
            rejected_words.append(enriched)

    events = [
        {
            "start": phrase["start"],
            "end": phrase["end"],
            "type": (
                "transcribed_phrase"
                if phrase["accepted_word_count"] > 0
                else "untranscribed_vocal"
            ),
            "phrase_index": phrase["index"],
        }
        for phrase in phrases
    ]

    payload = {
        "schema_version": CHOIR_SCHEMA_VERSION,
        "engine": CHOIR_ENGINE,
        "classifier": CHOIR_CLASSIFIER,
        "audio_hash": clean_hash,
        "source": str(backing),
        "lead_source": str(lead_audio),
        "backing_signature": _source_signature(backing),
        "lead_audio_signature": _source_signature(lead_audio),
        "lead_signature": _source_signature(lead_path),
        "timebase": "original_audio_seconds",
        "language": language,
        "model": str(model_name),
        "device": selected_device,
        "rollback_reference": {
            "git_head": (
                "9fedde9557e6ed9100ba29caaebcfcce848ef493"
            ),
            "engine": "ezscore-choir-whisper-small-v3",
            "schema_version": 3,
        },
        "parameters": {
            "sample_rate": TARGET_SAMPLE_RATE,
            "split_top_db": SPLIT_TOP_DB,
            "min_active_seconds": MIN_ACTIVE_SECONDS,
            "merge_gap_seconds": MERGE_GAP_SECONDS,
            "chunk_padding_seconds": CHUNK_PADDING_SECONDS,
            "max_chunk_seconds": MAX_CHUNK_SECONDS,
            "min_word_probability": MIN_WORD_PROBABILITY,
            "max_no_speech_probability": (
                MAX_NO_SPEECH_PROBABILITY
            ),
            "min_segment_avg_logprob": (
                MIN_SEGMENT_AVG_LOGPROB
            ),
            "classify_pad_seconds": CLASSIFY_PAD_SECONDS,
            "lead_match_pad_seconds": LEAD_MATCH_PAD_SECONDS,
            "min_temporal_overlap": MIN_TEMPORAL_OVERLAP,
            "min_doubling_backing_share": (
                MIN_DOUBLING_BACKING_SHARE
            ),
            "strong_doubling_backing_share": (
                STRONG_DOUBLING_BACKING_SHARE
            ),
            "min_distinct_backing_share": (
                MIN_DISTINCT_BACKING_SHARE
            ),
            "distinct_spectral_similarity": (
                DISTINCT_SPECTRAL_SIMILARITY
            ),
            "min_recoverable_backing_share": (
                MIN_RECOVERABLE_BACKING_SHARE
            ),
            "max_independent_correlation": (
                MAX_INDEPENDENT_CORRELATION
            ),
            "min_independent_residual_ratio": (
                MIN_INDEPENDENT_RESIDUAL_RATIO
            ),
            "min_independent_backing_activity": (
                MIN_INDEPENDENT_BACKING_ACTIVITY
            ),
        },
        "diagnostics": {
            **diagnostics,
            "raw_word_count": len(raw_words),
            "kept_word_count": len(words),
            "rejected_word_count": len(rejected_words),
            "classification_counts": classification_counts,
            "lead_rms_reference": (
                lead_signal.rms_reference
            ),
            "backing_rms_reference": (
                backing_signal.rms_reference
            ),
        },
        "phrases": phrases,
        "events": events,
        "words": words,
        "rejected_words": rejected_words,
        "word_count": len(words),
        "untranscribed_phrase_count": sum(
            1
            for phrase in phrases
            if not phrase["transcribed"]
        ),
    }

    output = choir_analysis_path(clean_hash)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse canonique des Chœurs EZScore V4.2."
    )
    parser.add_argument("--audio-hash", required=True)
    parser.add_argument("--backing", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--device", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    payload = analyze_choirs(
        audio_hash=args.audio_hash,
        backing_path=args.backing,
        force=bool(args.force),
        model_name=args.model,
        device=args.device,
    )

    print("CHOIR ANALYSIS V4.2")
    print("source     :", payload.get("source"))
    print("lead       :", payload.get("lead_source"))
    print("language   :", payload.get("language"))
    print("raw words  :", payload.get("diagnostics", {}).get("raw_word_count", 0))
    print("kept words :", payload.get("word_count", 0))
    print(
        "rejected   :",
        payload.get("diagnostics", {}).get("rejected_word_count", 0),
    )
    print(
        "classes    :",
        payload.get("diagnostics", {}).get("classification_counts", {}),
    )
    print("artifact   :", choir_analysis_path(args.audio_hash))
    print()

    for word in payload.get("words", []) or []:
        evidence = dict(word.get("source_evidence", {}) or {})
        print(
            f"KEEP "
            f"{float(word.get('start', 0.0)):8.2f} -> "
            f"{float(word.get('end', 0.0)):8.2f}  "
            f"{str(word.get('text', '')):<18} "
            f"{str(word.get('source_class', '')):<18} "
            f"share={float(evidence.get('backing_share', 0.0)):.2f} "
            f"sim={float(evidence.get('spectral_similarity', 0.0)):.2f} "
            f"corr={float(evidence.get('waveform_correlation', 0.0)):.2f} "
            f"res={float(evidence.get('residual_ratio', 0.0)):.2f}"
        )

    for word in payload.get("rejected_words", []) or []:
        evidence = dict(word.get("source_evidence", {}) or {})
        print(
            f"DROP "
            f"{float(word.get('start', 0.0)):8.2f} -> "
            f"{float(word.get('end', 0.0)):8.2f}  "
            f"{str(word.get('text', '')):<18} "
            f"{str(word.get('source_class', '')):<18} "
            f"lead={str(evidence.get('matched_lead_text', '')):<18} "
            f"share={float(evidence.get('backing_share', 0.0)):.2f} "
            f"sim={float(evidence.get('spectral_similarity', 0.0)):.2f} "
            f"corr={float(evidence.get('waveform_correlation', 0.0)):.2f} "
            f"res={float(evidence.get('residual_ratio', 0.0)):.2f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
