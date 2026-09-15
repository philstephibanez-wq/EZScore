"""Cached 4-stem separation for the EZScore analysis pipeline.

This module is intentionally additive. It does not modify the existing
EZScore rhythm, harmony, lyrics, structure, database, or UI workflows.

Canonical rule:
    the ORIGINAL uploaded audio remains the master timebase.

Stem responsibilities planned for the migration:
    vocals -> vocal melody / F0
    drums  -> rhythm / beat / measure analysis
    bass   -> auxiliary root evidence
    other  -> primary harmonic evidence

Lyrics are NOT transcribed from ``vocals.wav``. Whisper remains attached to
the original uploaded audio.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[2]
STEM_CACHE_DIR = APP_DIR / "data" / "analysis" / "stems"

STEM_SCHEMA_VERSION = 1
STEM_ENGINE = "demucs-4stems-v1"
DEFAULT_DEMUCS_MODEL = "htdemucs"
STEM_NAMES = ("vocals", "drums", "bass", "other")


def demucs_available() -> bool:
    """Return True when the current Python environment can import Demucs."""
    try:
        return importlib.util.find_spec("demucs") is not None
    except Exception:
        return False


def _safe_audio_hash(audio_hash: str) -> str:
    value = "".join(
        ch
        for ch in str(audio_hash or "").lower()
        if ch in "0123456789abcdef"
    )
    if value:
        return value
    return hashlib.sha256(str(audio_hash).encode("utf-8")).hexdigest()


def _safe_extension(extension: str) -> str:
    suffix = str(extension or ".mp3").strip().lower()
    if not suffix.startswith("."):
        suffix = "." + suffix
    if suffix not in {
        ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma"
    }:
        return ".bin"
    return suffix


def stem_cache_dir(
    audio_hash: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> Path:
    """Return the persistent cache directory for one song/model."""
    safe_hash = _safe_audio_hash(audio_hash)
    safe_model = "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in str(model or DEFAULT_DEMUCS_MODEL)
    )
    return STEM_CACHE_DIR / safe_hash / safe_model


def stem_manifest_path(
    audio_hash: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> Path:
    return stem_cache_dir(audio_hash, model=model) / "manifest.json"


def cached_stem_paths(
    audio_hash: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> dict[str, Path]:
    """Return only stems that actually exist in the persistent cache."""
    cache_dir = stem_cache_dir(audio_hash, model=model)
    result: dict[str, Path] = {}

    for name in STEM_NAMES:
        path = cache_dir / f"{name}.wav"
        if path.is_file() and path.stat().st_size > 0:
            result[name] = path

    return result


def stems_cache_complete(
    audio_hash: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> bool:
    paths = cached_stem_paths(audio_hash, model=model)
    return all(name in paths for name in STEM_NAMES)


def load_stem_manifest(
    audio_hash: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> dict[str, Any] | None:
    path = stem_manifest_path(audio_hash, model=model)
    if not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

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
    model: str = DEFAULT_DEMUCS_MODEL,
) -> None:
    """Delete only the cached stems for the requested song/model."""
    cache_dir = stem_cache_dir(audio_hash, model=model)
    shutil.rmtree(cache_dir, ignore_errors=True)


def _locate_demucs_output(
    output_root: Path,
    *,
    source_stem: str,
    model: str,
) -> dict[str, Path]:
    """Locate the four Demucs WAV files without assuming one CLI layout."""
    candidates = [
        output_root / model / source_stem,
        output_root / source_stem,
    ]

    # Defensive fallback for Demucs layout changes.
    candidates.extend(
        path
        for path in output_root.glob(f"**/{source_stem}")
        if path.is_dir()
    )

    for directory in candidates:
        found = {
            name: directory / f"{name}.wav"
            for name in STEM_NAMES
        }
        if all(path.is_file() and path.stat().st_size > 0 for path in found.values()):
            return found

    return {}


def _write_manifest(
    *,
    audio_hash: str,
    model: str,
    cache_dir: Path,
    source_extension: str,
    command: list[str],
) -> Path:
    payload = {
        "schema_version": STEM_SCHEMA_VERSION,
        "engine": STEM_ENGINE,
        "audio_hash": str(audio_hash),
        "timebase": "original_audio_seconds",
        "model": str(model),
        "source_extension": str(source_extension),
        "stems": {
            name: f"{name}.wav"
            for name in STEM_NAMES
        },
        "roles": {
            "vocals": "vocal_melody_f0",
            "drums": "rhythm_beats_measures",
            "bass": "auxiliary_root_evidence",
            "other": "primary_harmonic_evidence",
        },
        "lyrics_source": "original_audio",
        "command": list(command),
    }

    path = cache_dir / "manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def ensure_stems(
    *,
    audio_bytes: bytes,
    extension: str,
    audio_hash: str,
    model: str = DEFAULT_DEMUCS_MODEL,
    force: bool = False,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Return a persistent 4-stem cache, running Demucs at most once per hash.

    This function has no side effect on the EZScore DB and does not alter any
    canonical timeline. All stems begin on the same audio timebase as the
    original file produced by Demucs.

    Returns a serializable payload plus ``Path`` objects in ``paths``.
    """
    if not audio_bytes:
        raise ValueError("Audio vide.")

    if not demucs_available():
        raise RuntimeError(
            "Demucs n'est pas installé dans cet environnement Python. "
            "Le pipeline EZScore existant reste inchangé."
        )

    cache_dir = stem_cache_dir(audio_hash, model=model)

    if not force and stems_cache_complete(audio_hash, model=model):
        manifest = load_stem_manifest(audio_hash, model=model) or {}
        return {
            "status": "cached",
            "audio_hash": str(audio_hash),
            "model": str(model),
            "cache_dir": cache_dir,
            "paths": cached_stem_paths(audio_hash, model=model),
            "manifest": manifest,
        }

    suffix = _safe_extension(extension)

    # Never expose a partially separated set as a valid cache.
    parent = cache_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{cache_dir.name}.staging-",
            dir=str(parent),
        )
    )

    try:
        source = staging / f"source{suffix}"
        source.write_bytes(audio_bytes)

        output_root = staging / "demucs"
        command = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            str(model),
            "-o",
            str(output_root),
            str(source),
        ]

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
            tail = "\n".join(log.splitlines()[-30:])
            raise RuntimeError(
                f"Demucs a échoué (code {proc.returncode}).\n{tail}"
            )

        generated = _locate_demucs_output(
            output_root,
            source_stem=source.stem,
            model=str(model),
        )

        missing = [
            name
            for name in STEM_NAMES
            if name not in generated
        ]
        if missing:
            raise RuntimeError(
                "Demucs terminé mais stems manquants : "
                + ", ".join(missing)
            )

        payload_dir = staging / "payload"
        payload_dir.mkdir(parents=True, exist_ok=True)

        for name in STEM_NAMES:
            shutil.copy2(
                generated[name],
                payload_dir / f"{name}.wav",
            )

        _write_manifest(
            audio_hash=audio_hash,
            model=str(model),
            cache_dir=payload_dir,
            source_extension=suffix,
            command=command,
        )

        # Revalidate staging before replacing the persistent cache.
        for name in STEM_NAMES:
            path = payload_dir / f"{name}.wav"
            if not path.is_file() or path.stat().st_size <= 0:
                raise RuntimeError(
                    f"Stem invalide avant mise en cache : {name}"
                )

        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

        payload_dir.replace(cache_dir)

        return {
            "status": "generated",
            "audio_hash": str(audio_hash),
            "model": str(model),
            "cache_dir": cache_dir,
            "paths": cached_stem_paths(audio_hash, model=model),
            "manifest": load_stem_manifest(audio_hash, model=model) or {},
            "log_tail": "\n".join(log.splitlines()[-20:]),
        }

    finally:
        shutil.rmtree(staging, ignore_errors=True)


def stem_path(
    audio_hash: str,
    name: str,
    *,
    model: str = DEFAULT_DEMUCS_MODEL,
) -> Path | None:
    """Convenience accessor for future analysis modules."""
    if name not in STEM_NAMES:
        raise ValueError(
            f"Stem inconnu {name!r}; attendu: {', '.join(STEM_NAMES)}"
        )
    return cached_stem_paths(audio_hash, model=model).get(name)
