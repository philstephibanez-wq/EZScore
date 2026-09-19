"""Quality-first source separation for the EZScore analysis pipeline.

Primary model:
    BS-RoFormer-SW (openmirlab/bs-roformer-infer)

The model produces six stems.  EZScore keeps all raw stems and derives the
canonical four analysis stems:
    vocals
    drums
    bass
    other = guitar + piano + other

No model bytes are stored in Git.  bs-roformer-infer downloads its checkpoint
to its own cache and verifies SHA-256 before use.

The original uploaded audio remains the sole master timebase.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


APP_DIR = Path(__file__).resolve().parents[2]
STEM_CACHE_DIR = APP_DIR / "data" / "analysis" / "stems"

STEM_SCHEMA_VERSION = 2
STEM_ENGINE = "bs-roformer-sw-6stems-v1"
DEFAULT_STEM_MODEL = "roformer-model-bs-roformer-sw-by-jarredou"
# Compatibility alias: existing UI imports this historical symbol.
DEFAULT_DEMUCS_MODEL = DEFAULT_STEM_MODEL

STEM_NAMES = ("vocals", "drums", "bass", "other")
RAW_STEM_NAMES = ("vocals", "drums", "bass", "guitar", "piano", "other")


def quality_stem_engine_available() -> bool:
    try:
        return importlib.util.find_spec("bs_roformer") is not None
    except Exception:
        return False


def demucs_available() -> bool:
    """Compatibility alias used by the current analysis UI."""
    return quality_stem_engine_available()


def _safe_audio_hash(audio_hash: str) -> str:
    value = "".join(
        ch for ch in str(audio_hash or "").lower()
        if ch in "0123456789abcdef"
    )
    return value or hashlib.sha256(str(audio_hash).encode("utf-8")).hexdigest()


def _safe_model(model: str) -> str:
    return "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in str(model or DEFAULT_STEM_MODEL)
    )


def stem_cache_dir(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> Path:
    return STEM_CACHE_DIR / _safe_audio_hash(audio_hash) / _safe_model(model)


def stem_manifest_path(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> Path:
    return stem_cache_dir(audio_hash, model=model) / "manifest.json"


def cached_stem_paths(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> dict[str, Path]:
    cache_dir = stem_cache_dir(audio_hash, model=model)
    result: dict[str, Path] = {}
    for name in STEM_NAMES:
        path = cache_dir / f"{name}.wav"
        if path.is_file() and path.stat().st_size > 0:
            result[name] = path
    return result


def raw_stem_paths(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> dict[str, Path]:
    raw_dir = stem_cache_dir(audio_hash, model=model) / "raw"
    result: dict[str, Path] = {}
    for name in RAW_STEM_NAMES:
        path = raw_dir / f"{name}.wav"
        if path.is_file() and path.stat().st_size > 0:
            result[name] = path
    return result


def stems_cache_complete(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> bool:
    paths = cached_stem_paths(audio_hash, model=model)
    return all(name in paths for name in STEM_NAMES)


def load_stem_manifest(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> dict[str, Any] | None:
    path = stem_manifest_path(audio_hash, model=model)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("schema_version", 0) or 0) != STEM_SCHEMA_VERSION:
        return None
    if str(payload.get("engine", "")) != STEM_ENGINE:
        return None
    if not stems_cache_complete(audio_hash, model=model):
        return None
    return payload


def delete_stem_cache(
    audio_hash: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> None:
    shutil.rmtree(stem_cache_dir(audio_hash, model=model), ignore_errors=True)


def _pick_raw_stem(output_dir: Path, source_stem: str, target: str) -> Path:
    candidates = []
    target_low = target.lower()
    source_low = source_stem.lower()
    for path in output_dir.rglob("*.wav"):
        name = path.stem.lower()
        if target_low not in name:
            continue
        score = 0
        if source_low in name:
            score += 4
        if name.endswith("_" + target_low) or name == target_low:
            score += 3
        if target_low in {"vocals", "drums", "bass", "guitar", "piano", "other"}:
            score += 1
        candidates.append((score, path.stat().st_size, path))

    if not candidates:
        raise RuntimeError(
            f"BS-RoFormer terminé mais stem `{target}` introuvable dans {output_dir}."
        )
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def _sum_audio(paths: list[Path], destination: Path) -> None:
    arrays = []
    sample_rate = None
    channels = None
    length = None

    for path in paths:
        data, sr = sf.read(str(path), always_2d=True, dtype="float32")
        if sample_rate is None:
            sample_rate = int(sr)
            channels = int(data.shape[1])
            length = int(data.shape[0])
        elif int(sr) != sample_rate or data.shape[1] != channels:
            raise RuntimeError(
                "Stems BS-RoFormer incompatibles pour recombinaison : "
                f"{path.name} a {sr} Hz / {data.shape[1]} canaux."
            )
        if data.shape[0] != length:
            raise RuntimeError(
                "Stems BS-RoFormer de longueurs différentes : "
                f"{path.name}={data.shape[0]}, attendu={length}."
            )
        arrays.append(data)

    if not arrays or sample_rate is None:
        raise RuntimeError("Aucun stem à recombiner.")

    mixed = np.sum(np.stack(arrays, axis=0), axis=0)
    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 1.0:
        mixed = mixed / peak

    sf.write(str(destination), mixed, sample_rate, subtype="FLOAT")


def _write_manifest(
    *,
    audio_hash: str,
    model: str,
    cache_dir: Path,
    device: str,
    cache_info: dict[str, Any],
) -> None:
    payload = {
        "schema_version": STEM_SCHEMA_VERSION,
        "engine": STEM_ENGINE,
        "audio_hash": str(audio_hash),
        "timebase": "original_audio_seconds",
        "model": str(model),
        "device": str(device),
        "model_cache": cache_info,
        "canonical_stems": {
            "vocals": "vocals.wav",
            "drums": "drums.wav",
            "bass": "bass.wav",
            "other": "other.wav",
        },
        "raw_stems": {
            name: f"raw/{name}.wav"
            for name in RAW_STEM_NAMES
        },
        "other_derivation": "guitar + piano + other",
        "roles": {
            "vocals": "lyrics_reference_and_future_vocal_analysis",
            "drums": "rhythm_beats_measures",
            "bass": "auxiliary_root_evidence",
            "other": "harmonic_accompaniment",
        },
        "lyrics_source": "original_audio",
    }
    path = cache_dir / "manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _require_model_root() -> Path:
    value = str(os.getenv("BS_ROFORMER_MODELS_PATH", "") or "").strip()
    if not value:
        raise RuntimeError(
            "BS_ROFORMER_MODELS_PATH n'est pas défini. "
            "Exemple attendu : H:\\EZScoreModels\\bs-roformer."
        )
    root = Path(value).expanduser()
    if root.drive and root.drive.upper() == "C:":
        raise RuntimeError(
            "BS_ROFORMER_MODELS_PATH pointe vers C:. "
            "Les modèles EZScore doivent rester hors du disque système."
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _runtime_temp_root() -> Path:
    value = str(os.getenv("EZSCORE_RUNTIME_TMP", "") or "").strip()
    if value:
        root = Path(value).expanduser()
    else:
        model_root = _require_model_root()
        root = model_root.parent / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_checked(command: list[str], *, timeout_seconds: int) -> str:
    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=int(timeout_seconds),
        check=False,
    )
    log = proc.stdout or ""
    if proc.returncode != 0:
        tail = "\\n".join(log.splitlines()[-80:])
        raise RuntimeError(
            "Commande d'analyse échouée "
            f"(code {proc.returncode}) : {' '.join(command)}\\n{tail}"
        )
    return log


def _convert_to_wav(source: Path, destination: Path, *, timeout_seconds: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg est requis pour préparer l'entrée WAV de BS-RoFormer."
        )
    _run_checked(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(source),
            "-vn",
            "-acodec", "pcm_f32le",
            str(destination),
        ],
        timeout_seconds=timeout_seconds,
    )
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise RuntimeError("Conversion WAV BS-RoFormer invalide.")


def ensure_stems(
    *,
    audio_bytes: bytes,
    extension: str,
    audio_hash: str,
    model: str = DEFAULT_STEM_MODEL,
    force: bool = False,
    force_model_download: bool = False,
    timeout_seconds: int = 7200,
) -> dict[str, Any]:
    """Generate/cache quality-first six-stem RoFormer analysis.

    bs-roformer-infer 0.1.3 exposes MODEL_REGISTRY plus its download and
    inference entry points.  It does not expose BSRoformerSession.
    """
    if not audio_bytes:
        raise ValueError("Audio vide.")

    if not quality_stem_engine_available():
        raise RuntimeError(
            "Moteur STEM haute qualité absent : installez `bs-roformer-infer`. "
            "EZScore refuse de revenir silencieusement à Demucs."
        )

    cache_dir = stem_cache_dir(audio_hash, model=model)
    if not force and stems_cache_complete(audio_hash, model=model):
        return {
            "status": "cached",
            "audio_hash": str(audio_hash),
            "model": str(model),
            "cache_dir": cache_dir,
            "paths": cached_stem_paths(audio_hash, model=model),
            "manifest": load_stem_manifest(audio_hash, model=model) or {},
        }

    from bs_roformer import MODEL_REGISTRY

    try:
        entry = MODEL_REGISTRY.get(model)
    except KeyError as exc:
        raise RuntimeError(f"Modèle BS-RoFormer inconnu : {model!r}.") from exc

    model_root = _require_model_root()
    model_dir = model_root / entry.slug
    config_path = model_dir / entry.config
    checkpoint_path = model_dir / entry.checkpoint

    if force_model_download or not config_path.is_file() or not checkpoint_path.is_file():
        cmd = [
            sys.executable,
            "-m", "bs_roformer.download",
            "--model", entry.slug,
            "--output-dir", str(model_root),
        ]
        if force_model_download:
            cmd.append("--force")
        _run_checked(cmd, timeout_seconds=max(1800, int(timeout_seconds)))

    if not config_path.is_file():
        raise RuntimeError(f"Config BS-RoFormer absente : {config_path}")
    if not checkpoint_path.is_file():
        raise RuntimeError(f"Checkpoint BS-RoFormer absent : {checkpoint_path}")

    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f"ezscore-{cache_dir.name}-",
            dir=str(_runtime_temp_root()),
        )
    )

    device = str(os.getenv("EZSCORE_STEM_DEVICE", "cuda:0") or "cuda:0").strip()

    try:
        input_dir = staging / "input"
        output_dir = staging / "roformer_output"
        payload_dir = staging / "payload"
        raw_dir = payload_dir / "raw"
        input_dir.mkdir()
        output_dir.mkdir()
        raw_dir.mkdir(parents=True)

        suffix = str(extension or ".mp3").strip().lower()
        if not suffix.startswith("."):
            suffix = "." + suffix

        original = staging / f"source{suffix}"
        original.write_bytes(audio_bytes)

        wav_source = input_dir / "source.wav"
        _convert_to_wav(
            original,
            wav_source,
            timeout_seconds=min(900, max(120, int(timeout_seconds))),
        )

        inference_log = _run_checked(
            [
                sys.executable,
                "-m", "bs_roformer.inference",
                "--config_path", str(config_path),
                "--model_path", str(checkpoint_path),
                "--input_folder", str(input_dir),
                "--store_dir", str(output_dir),
                "--device", device,
            ],
            timeout_seconds=max(1800, int(timeout_seconds)),
        )

        located = {
            name: _pick_raw_stem(output_dir, wav_source.stem, name)
            for name in RAW_STEM_NAMES
        }

        for name, path in located.items():
            shutil.copy2(path, raw_dir / f"{name}.wav")

        shutil.copy2(raw_dir / "vocals.wav", payload_dir / "vocals.wav")
        shutil.copy2(raw_dir / "drums.wav", payload_dir / "drums.wav")
        shutil.copy2(raw_dir / "bass.wav", payload_dir / "bass.wav")
        _sum_audio(
            [
                raw_dir / "guitar.wav",
                raw_dir / "piano.wav",
                raw_dir / "other.wav",
            ],
            payload_dir / "other.wav",
        )

        for name in STEM_NAMES:
            path = payload_dir / f"{name}.wav"
            if not path.is_file() or path.stat().st_size <= 0:
                raise RuntimeError(f"Stem canonique invalide : {name}")

        _write_manifest(
            audio_hash=audio_hash,
            model=model,
            cache_dir=payload_dir,
            device=device,
            cache_info={
                "root": str(model_root),
                "slug": str(entry.slug),
                "config": str(config_path),
                "checkpoint": str(checkpoint_path),
            },
        )

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        payload_dir.replace(cache_dir)

        return {
            "status": "generated",
            "audio_hash": str(audio_hash),
            "model": str(model),
            "cache_dir": cache_dir,
            "paths": cached_stem_paths(audio_hash, model=model),
            "manifest": load_stem_manifest(audio_hash, model=model) or {},
            "log_tail": "\\n".join(inference_log.splitlines()[-30:]),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def stem_path(
    audio_hash: str,
    name: str,
    *,
    model: str = DEFAULT_STEM_MODEL,
) -> Path | None:
    if name not in STEM_NAMES:
        raise ValueError(
            f"Stem inconnu {name!r}; attendu: {', '.join(STEM_NAMES)}"
        )
    return cached_stem_paths(audio_hash, model=model).get(name)
