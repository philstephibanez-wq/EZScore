from __future__ import annotations

"""Canonical forced alignment of user-supplied lyrics.

No free transcription and no audio language detection are performed here.

Pipeline:
    user lyrics
        -> uroman universal romanization
        -> MMS_FA multilingual acoustic forced alignment
        -> canonical word timestamps on original-audio seconds

The acoustic reference is lead_vocals.wav. The original spelling supplied by
the user is preserved for display; romanized/normalized forms are internal
alignment data only.
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torchaudio

from ezscore.analysis.vocal_stems import vocal_stem_paths


ENGINE = "torchaudio-mms-fa"
MODEL = "MMS_FA"
SCHEMA_VERSION = 1
TIMEBASE = "original_audio_seconds"

APP_DIR = Path(__file__).resolve().parents[2]
LAB_CACHE_DIR = APP_DIR / "data" / "analysis" / "stem_lab"
DB_PATH = APP_DIR / "data" / "EZScore.sqlite3"


def work_dir(audio_hash: str) -> Path:
    path = LAB_CACHE_DIR / str(audio_hash)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_path(audio_hash: str) -> Path:
    return work_dir(audio_hash) / "lyrics_forced_alignment.json"


def draft_path(audio_hash: str) -> Path:
    return work_dir(audio_hash) / "lyrics_input.txt"


def _ensure_source_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_lyrics_sources (
            audio_hash TEXT PRIMARY KEY,
            source_text TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )


def load_persisted_source_text(audio_hash: str) -> str:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            _ensure_source_table(conn)
            row = conn.execute(
                "SELECT source_text FROM user_lyrics_sources WHERE audio_hash = ?",
                (str(audio_hash),),
            ).fetchone()
    except sqlite3.Error:
        return ""
    return str(row[0] or "") if row else ""


def save_persisted_source_text(audio_hash: str, text: str) -> None:
    value = str(text or "")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            _ensure_source_table(conn)
            conn.execute(
                """
                INSERT INTO user_lyrics_sources (audio_hash, source_text, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(audio_hash) DO UPDATE SET
                    source_text = excluded.source_text,
                    updated_at = excluded.updated_at
                """,
                (str(audio_hash), value, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
    except sqlite3.Error:
        pass


def load_draft(audio_hash: str) -> str:
    path = draft_path(audio_hash)
    if path.is_file():
        value = path.read_text(encoding="utf-8")
        if value.strip():
            return value

    payload = load_alignment(audio_hash)
    if payload:
        value = str(payload.get("source_text", "") or "")
        if value.strip():
            return value

    return load_persisted_source_text(audio_hash)


def save_draft(audio_hash: str, text: str) -> None:
    value = str(text or "")
    draft_path(audio_hash).write_text(value, encoding="utf-8")
    save_persisted_source_text(audio_hash, value)


def load_alignment(audio_hash: str) -> dict[str, Any] | None:
    path = cache_path(audio_hash)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    words = list(payload.get("words", []) or [])
    if not (
        int(payload.get("speech_cache_schema_version", 0) or 0)
        == SCHEMA_VERSION
        and str(payload.get("engine", "") or "") == ENGINE
        and str(payload.get("status", "") or "") == "complete"
        and str(payload.get("audio_hash", "") or "") == str(audio_hash)
        and str(payload.get("timebase", "") or "") == TIMEBASE
        and words
    ):
        return None
    return payload


def alignment_is_current(audio_hash: str, text: str | None = None) -> bool:
    payload = load_alignment(audio_hash)
    if payload is None:
        return False
    if text is not None:
        return (
            str(payload.get("source_text", "") or "").strip()
            == str(text or "").strip()
        )
    return True


def invalidate_dependents(audio_hash: str) -> None:
    """Invalidate only semantic artifacts derived from word timestamps."""
    work = work_dir(audio_hash)
    for name in (
        "structure_analysis.json",
        "karaoke_conductor.json",
        "choir_analysis.json",
        "choir_words_from_vocals.json",
        "whisper_backing_small.json",
    ):
        try:
            (work / name).unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _models_root() -> Path:
    explicit = str(os.environ.get("EZSCORE_MODELS_PATH", "") or "").strip()
    if explicit:
        base = Path(explicit)
    else:
        base = APP_DIR.parent / "EZScoreModels"
    path = base / "torch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _romanizer():
    try:
        import uroman as ur
    except Exception as exc:
        raise RuntimeError(
            "Le paquet `uroman` est requis pour l'alignement multilingue. "
            "Installez requirements-forced-alignment.txt."
        ) from exc
    return ur.Uroman()


def _normalize_acoustic(value: str) -> str:
    value = str(value or "").lower().replace("’", "'")
    value = re.sub(r"[^a-z' ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _source_tokens(source_text: str) -> list[dict[str, Any]]:
    """Preserve user words/line breaks while producing acoustic forms."""
    romanizer = _romanizer()
    rows: list[dict[str, Any]] = []

    for line_index, line in enumerate(str(source_text or "").splitlines()):
        for raw in re.findall(r"\S+", line):
            romanized = str(romanizer.romanize_string(raw) or "")
            acoustic = _normalize_acoustic(romanized).replace(" ", "")
            if not acoustic:
                continue
            rows.append(
                {
                    "text": raw,
                    "acoustic": acoustic,
                    "line_index": int(line_index),
                }
            )

    if not rows:
        raise RuntimeError("Le texte fourni ne contient aucun mot alignable.")
    return rows


def _lead_path(audio_hash: str) -> Path:
    stems = vocal_stem_paths(audio_hash)
    lead = stems.get("lead_vocals")
    if lead and Path(lead).is_file():
        return Path(lead)

    raise RuntimeError(
        "lead_vocals.wav est absent. "
        "Terminez d'abord l'étape STEM Chant / Chœurs."
    )


def _load_lead(audio_hash: str, sample_rate: int):
    waveform, sr = torchaudio.load(str(_lead_path(audio_hash)))
    if waveform.ndim != 2 or waveform.shape[-1] <= 0:
        raise RuntimeError("STEM Chant vide ou illisible.")

    waveform = waveform.to(torch.float32)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    if int(sr) != int(sample_rate):
        waveform = torchaudio.functional.resample(
            waveform,
            int(sr),
            int(sample_rate),
        )
    return waveform


def _emit_chunked(model, waveform, device, *, sample_rate: int, progress=None):
    """Run MMS_FA in bounded chunks so a full song fits on a 6 GB GPU."""
    chunk_seconds = 20.0
    chunk_samples = max(1, int(round(chunk_seconds * sample_rate)))

    emissions = []
    frame_map: list[dict[str, int]] = []
    cumulative_frames = 0
    total_samples = int(waveform.shape[-1])
    total_chunks = max(1, (total_samples + chunk_samples - 1) // chunk_samples)

    with torch.inference_mode():
        for chunk_index, sample_start in enumerate(range(0, total_samples, chunk_samples), start=1):
            if progress is not None:
                progress(f"Analyse acoustique MMS_FA · segment {chunk_index}/{total_chunks}…")
            sample_end = min(total_samples, sample_start + chunk_samples)
            chunk = waveform[:, sample_start:sample_end].to(device)
            emission, _ = model(chunk)
            emission_cpu = emission[0].detach().to("cpu")
            frame_count = int(emission_cpu.shape[0])
            if frame_count <= 0:
                continue

            emissions.append(emission_cpu)
            frame_map.append(
                {
                    "frame_start": cumulative_frames,
                    "frame_end": cumulative_frames + frame_count,
                    "sample_start": sample_start,
                    "sample_end": sample_end,
                }
            )
            cumulative_frames += frame_count

            del chunk, emission
            if device.type == "cuda":
                torch.cuda.empty_cache()

    if not emissions:
        raise RuntimeError("MMS_FA n'a produit aucune émission acoustique.")

    return torch.cat(emissions, dim=0), frame_map


def _frame_seconds(
    frame: int,
    frame_map: list[dict[str, int]],
    sample_rate: int,
) -> float:
    if not frame_map:
        return 0.0

    value = max(0, int(frame))
    row = frame_map[-1]
    for candidate in frame_map:
        if value < candidate["frame_end"]:
            row = candidate
            break

    local_frame = max(
        0,
        min(
            value - row["frame_start"],
            row["frame_end"] - row["frame_start"],
        ),
    )
    frame_count = max(1, row["frame_end"] - row["frame_start"])
    sample_count = max(1, row["sample_end"] - row["sample_start"])
    sample = row["sample_start"] + (local_frame / frame_count) * sample_count
    return float(sample) / float(sample_rate)


def _span_score(spans) -> float:
    weighted = 0.0
    weight = 0
    for span in spans:
        length = max(1, int(span.end) - int(span.start))
        weighted += float(span.score) * length
        weight += length
    return weighted / max(1, weight)


def align_user_lyrics(audio_hash: str, source_text: str, *, progress=None) -> dict[str, Any]:
    """Align exact user lyrics against lead_vocals.wav."""
    source_text = str(source_text or "").strip()
    if not source_text:
        raise RuntimeError("Collez d'abord le texte exact du chant.")

    if progress is not None:
        progress("Préparation phonétique du texte…")
    rows = _source_tokens(source_text)
    transcript = [str(row["acoustic"]) for row in rows]

    if progress is not None:
        progress("Chargement du modèle MMS_FA…")
    bundle = torchaudio.pipelines.MMS_FA
    sample_rate = int(bundle.sample_rate)
    waveform = _load_lead(audio_hash, sample_rate)

    # Keep large Torch downloads off C:.
    torch.hub.set_dir(str(_models_root()))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = bundle.get_model().to(device).eval()
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    emission, frame_map = _emit_chunked(
        model,
        waveform,
        device,
        sample_rate=sample_rate,
        progress=progress,
    )

    if progress is not None:
        progress("Alignement forcé texte ↔ chant…")

    try:
        tokenized = tokenizer(transcript)
        token_spans = aligner(emission, tokenized)
    except Exception as exc:
        raise RuntimeError(
            "MMS_FA n'a pas pu aligner le texte fourni sur le Chant. "
            "Vérifiez que le texte correspond bien à ce qui est réellement chanté."
        ) from exc

    if len(token_spans) != len(rows):
        raise RuntimeError(
            "Alignement incomplet : le nombre de mots acoustiques ne correspond "
            "pas au texte fourni."
        )

    words: list[dict[str, Any]] = []
    previous_end = 0.0

    for row, spans in zip(rows, token_spans):
        spans = list(spans or [])
        if not spans:
            continue

        start = _frame_seconds(int(spans[0].start), frame_map, sample_rate)
        end = _frame_seconds(int(spans[-1].end), frame_map, sample_rate)

        # Canonical word intervals are monotonic and non-overlapping.
        start = max(previous_end, float(start))
        end = max(start + 0.010, float(end))
        previous_end = end

        words.append(
            {
                "start": round(start, 6),
                "end": round(end, 6),
                "text": str(row["text"]),
                "line_index": int(row["line_index"]),
                "confidence": round(_span_score(spans), 6),
                "acoustic": str(row["acoustic"]),
            }
        )

    if not words:
        raise RuntimeError("Aucun mot n'a pu être aligné.")

    payload = {
        "speech_cache_schema_version": SCHEMA_VERSION,
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "engine": ENGINE,
        "model": MODEL,
        "source": "user_text+lead_vocals",
        "audio_hash": str(audio_hash),
        "timebase": TIMEBASE,
        "language": "user-text-multilingual",
        "source_text": source_text,
        "text": source_text,
        "word_count": len(words),
        "words": words,
        "alignment": {
            "romanizer": "uroman",
            "language_detection": "none",
            "transcription": "none",
            "acoustic_source": "lead_vocals.wav",
            "sample_rate": sample_rate,
            "chunk_seconds": 20.0,
        },
    }

    if progress is not None:
        progress("Enregistrement des mots horodatés…")

    path = cache_path(audio_hash)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)

    save_draft(audio_hash, source_text)
    invalidate_dependents(audio_hash)
    return payload
