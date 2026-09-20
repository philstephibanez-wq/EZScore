"""Dedicated canonical choir/backing-vocal analyzer for EZScore."""

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

CHOIR_SCHEMA_VERSION = 3
CHOIR_ENGINE = "ezscore-choir-whisper-small-v3"
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


class ChoirAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class TimeRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, float(self.end) - float(self.start))


def _clean_hash(audio_hash: str) -> str:
    value = "".join(
        ch for ch in str(audio_hash or "").lower()
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
    lead = lead_transcript_path(audio_hash)

    if not backing.is_file() or not lead.is_file():
        return False

    return (
        dict(payload.get("backing_signature", {}) or {}) == _source_signature(backing)
        and dict(payload.get("lead_signature", {}) or {}) == _source_signature(lead)
    )


def delete_choir_analysis(audio_hash: str) -> None:
    try:
        choir_analysis_path(audio_hash).unlink()
    except FileNotFoundError:
        pass


def _load_master_language(audio_hash: str) -> tuple[str, Path]:
    path = lead_transcript_path(audio_hash)
    if not path.is_file():
        raise ChoirAnalysisError(
            "Analyse Chant principale absente : whisper_original_small.json requis."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    language = str(payload.get("language", "") or "").strip().lower()
    if not language:
        raise ChoirAnalysisError(
            "Langue Chant principale absente : impossible d'analyser les Chœurs."
        )
    return language, path


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


def detect_vocal_activity(
    backing_path: Path,
) -> tuple[np.ndarray, int, list[TimeRange], dict[str, float]]:
    path = Path(backing_path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise ChoirAnalysisError(f"Stem Chœurs invalide : {path}")

    y, sr = librosa.load(str(path), sr=TARGET_SAMPLE_RATE, mono=True)
    y = np.asarray(y, dtype=np.float32)
    if y.size == 0:
        raise ChoirAnalysisError("Stem Chœurs vide.")

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

    rms = librosa.feature.rms(
        y=y,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH,
    )[0]
    positive = rms[rms > 1e-9]
    active_seconds = float(sum(item.duration for item in merged))

    diagnostics = {
        "duration_seconds": duration,
        "active_seconds": active_seconds,
        "active_ratio": active_seconds / duration if duration > 0.0 else 0.0,
        "rms_median": float(np.median(positive)) if positive.size else 0.0,
        "rms_p75": float(np.percentile(positive, 75)) if positive.size else 0.0,
        "rms_p95": float(np.percentile(positive, 95)) if positive.size else 0.0,
    }
    return y, int(sr), chunks, diagnostics


@lru_cache(maxsize=2)
def _whisper_model(model_name: str, device: str):
    return whisper.load_model(str(model_name), device=str(device))


def _deduplicate_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            if str(previous.get("text", "")).casefold() != text.casefold():
                continue

            p0 = float(previous.get("start", 0.0) or 0.0)
            p1 = float(previous.get("end", p0) or p0)
            overlap = max(0.0, min(end, p1) - max(start, p0))
            shorter = max(0.001, min(end - start, p1 - p0))
            if overlap / shorter >= 0.70:
                duplicate = True
                if float(word.get("confidence", 0.0) or 0.0) > float(
                    previous.get("confidence", 0.0) or 0.0
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
    start = max(0.0, float(item.start) - CHUNK_PADDING_SECONDS)
    end = min(duration, float(item.end) + CHUNK_PADDING_SECONDS)
    i0 = max(0, int(round(start * sr)))
    i1 = min(y.size, int(round(end * sr)))
    return np.asarray(y[i0:i1], dtype=np.float32), start


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

    if backing_path is None:
        backing_path = vocal_stem_paths(clean_hash).get("backing_vocals")
    if backing_path is None:
        raise ChoirAnalysisError(
            "backing_vocals.wav absent : exécuter d'abord la séparation Chant / Chœurs."
        )

    backing = Path(backing_path)
    language, lead_path = _load_master_language(clean_hash)
    y, sr, chunks, diagnostics = detect_vocal_activity(backing)

    selected_device = str(
        device or ("cuda" if torch.cuda.is_available() else "cpu")
    )
    model = _whisper_model(str(model_name), selected_device)

    words: list[dict[str, Any]] = []
    phrases: list[dict[str, Any]] = []

    for index, active in enumerate(chunks):
        audio_chunk, chunk_start = _chunk_signal(y, sr, active)
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
            no_speech = float(segment.get("no_speech_prob", 0.0) or 0.0)
            avg_logprob = float(segment.get("avg_logprob", 0.0) or 0.0)
            if no_speech > MAX_NO_SPEECH_PROBABILITY:
                continue
            if avg_logprob < MIN_SEGMENT_AVG_LOGPROB:
                continue

            for raw_word in segment.get("words", []) or []:
                text = str(raw_word.get("word", "") or "").strip()
                local_start = float(raw_word.get("start", 0.0) or 0.0)
                local_end = float(raw_word.get("end", local_start) or local_start)
                confidence = float(raw_word.get("probability", 0.0) or 0.0)

                if not text or local_end <= local_start:
                    continue
                if confidence < MIN_WORD_PROBABILITY:
                    continue

                start = chunk_start + local_start
                end = chunk_start + local_end
                center = (start + end) / 2.0

                if not (float(active.start) <= center <= float(active.end)):
                    continue

                words.append(
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

    words = _deduplicate_words(words)
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
        "audio_hash": clean_hash,
        "source": str(backing),
        "backing_signature": _source_signature(backing),
        "lead_signature": _source_signature(lead_path),
        "timebase": "original_audio_seconds",
        "language": language,
        "model": str(model_name),
        "device": selected_device,
        "parameters": {
            "sample_rate": TARGET_SAMPLE_RATE,
            "split_top_db": SPLIT_TOP_DB,
            "min_active_seconds": MIN_ACTIVE_SECONDS,
            "merge_gap_seconds": MERGE_GAP_SECONDS,
            "chunk_padding_seconds": CHUNK_PADDING_SECONDS,
            "max_chunk_seconds": MAX_CHUNK_SECONDS,
            "min_word_probability": MIN_WORD_PROBABILITY,
            "max_no_speech_probability": MAX_NO_SPEECH_PROBABILITY,
            "min_segment_avg_logprob": MIN_SEGMENT_AVG_LOGPROB,
        },
        "diagnostics": diagnostics,
        "phrases": phrases,
        "events": events,
        "words": words,
        "word_count": len(words),
        "untranscribed_phrase_count": sum(
            1 for phrase in phrases if not phrase["transcribed"]
        ),
    }

    output = choir_analysis_path(clean_hash)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse canonique des Chœurs EZScore.")
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

    print("CHOIR ANALYSIS")
    print("source   :", payload.get("source"))
    print("language :", payload.get("language"))
    print("phrases  :", len(payload.get("phrases", []) or []))
    print("words    :", payload.get("word_count", 0))
    print("artifact :", choir_analysis_path(args.audio_hash))
    for word in payload.get("words", []) or []:
        print(
            f"{float(word.get('start', 0.0)):8.2f} -> "
            f"{float(word.get('end', 0.0)):8.2f}  "
            f"{float(word.get('confidence', 0.0)):0.2f}  "
            f"{word.get('text', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
