"""Lead/backing vocal separation for EZScore via MelBand-RoFormer."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ezscore.analysis.stems import stem_cache_dir

DEFAULT_KARAOKE_MODEL = "roformer-model-melband-roformer-karaoke-by-becruily"
VOCAL_STEM_NAMES = ("lead_vocals", "backing_vocals")
VOCAL_SPLIT_DIRNAME = "vocal_split"


def vocal_split_dir(audio_hash: str) -> Path:
    return stem_cache_dir(audio_hash) / VOCAL_SPLIT_DIRNAME


def vocal_stem_paths(audio_hash: str) -> dict[str, Path]:
    root = vocal_split_dir(audio_hash)
    result: dict[str, Path] = {}
    for name in VOCAL_STEM_NAMES:
        path = root / f"{name}.wav"
        if path.is_file() and path.stat().st_size > 0:
            result[name] = path
    return result


def vocal_stems_cache_complete(audio_hash: str) -> bool:
    paths = vocal_stem_paths(audio_hash)
    return all(name in paths for name in VOCAL_STEM_NAMES)


def delete_vocal_stem_cache(audio_hash: str) -> None:
    shutil.rmtree(vocal_split_dir(audio_hash), ignore_errors=True)


def karaoke_engine_available() -> bool:
    try:
        return importlib.util.find_spec("mel_band_roformer") is not None
    except Exception:
        return False


def _model_root() -> Path:
    explicit = str(os.getenv("MELBAND_ROFORMER_MODELS_PATH", "") or "").strip()
    if explicit:
        root = Path(explicit).expanduser()
    else:
        bs_root = str(os.getenv("BS_ROFORMER_MODELS_PATH", "") or "").strip()
        if not bs_root:
            raise RuntimeError(
                "MELBAND_ROFORMER_MODELS_PATH ou BS_ROFORMER_MODELS_PATH doit être défini."
            )
        root = Path(bs_root).expanduser().parent / "melband-roformer"

    if root.drive and root.drive.upper() == "C:":
        raise RuntimeError("Le cache MelBand-RoFormer ne doit pas être placé sur C:.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _runtime_temp_root() -> Path:
    explicit = str(os.getenv("EZSCORE_RUNTIME_TMP", "") or "").strip()
    if explicit:
        root = Path(explicit).expanduser()
    else:
        bs_root = str(os.getenv("BS_ROFORMER_MODELS_PATH", "") or "").strip()
        if not bs_root:
            raise RuntimeError("BS_ROFORMER_MODELS_PATH doit être défini.")
        root = Path(bs_root).expanduser().parent / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_checked(command: list[str], *, timeout_seconds: int) -> str:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=int(timeout_seconds),
        check=False,
    )
    log = proc.stdout or ""
    if proc.returncode != 0:
        tail = "\n".join(log.splitlines()[-100:])
        raise RuntimeError(
            "Séparation Chant / Chœurs échouée "
            f"(code {proc.returncode}).\n{tail}"
        )
    return log


def _find_output(output_dir: Path, output_id: str) -> Path:
    candidates = sorted(
        p for p in output_dir.rglob("*.wav")
        if p.stem.casefold().endswith("_" + output_id.casefold())
    )
    if len(candidates) != 1:
        all_wavs = ", ".join(sorted(p.name for p in output_dir.rglob("*.wav")))
        raise RuntimeError(
            f"Sortie MelBand `{output_id}` ambiguë/absente. "
            f"WAV produits : {all_wavs or 'aucun'}"
        )
    return candidates[0]


def ensure_vocal_stems(
    *,
    audio_hash: str,
    vocals_path: Path,
    model: str = DEFAULT_KARAOKE_MODEL,
    force: bool = False,
    force_model_download: bool = False,
    timeout_seconds: int = 7200,
) -> dict[str, Any]:
    vocals_path = Path(vocals_path)
    if not vocals_path.is_file() or vocals_path.stat().st_size <= 0:
        raise RuntimeError(f"Stem vocals invalide : {vocals_path}")

    if not karaoke_engine_available():
        raise RuntimeError(
            "Moteur Chant / Chœurs absent : installez `melband-roformer-infer`."
        )

    if not force and vocal_stems_cache_complete(audio_hash):
        return {
            "status": "cached",
            "model": model,
            "paths": vocal_stem_paths(audio_hash),
        }

    from mel_band_roformer import MODEL_REGISTRY

    try:
        entry = MODEL_REGISTRY.get(model)
    except KeyError as exc:
        available = [item.slug for item in MODEL_REGISTRY.list("karaoke")]
        raise RuntimeError(
            f"Modèle karaoke MelBand inconnu : {model!r}. "
            f"Disponibles : {', '.join(available) or 'aucun'}"
        ) from exc

    model_root = _model_root()
    target = vocal_split_dir(audio_hash)
    target.parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(
            prefix="ezscore-vocal-split-",
            dir=str(_runtime_temp_root()),
        )
    )

    device = str(os.getenv("EZSCORE_STEM_DEVICE", "cuda:0") or "cuda:0").strip()

    try:
        input_dir = staging / "input"
        output_dir = staging / "output"
        payload_dir = staging / "payload"
        input_dir.mkdir()
        output_dir.mkdir()
        payload_dir.mkdir()

        shutil.copy2(vocals_path, input_dir / "vocals.wav")

        if force_model_download:
            _run_checked(
                [
                    sys.executable,
                    "-m", "mel_band_roformer.download",
                    "--model", entry.slug,
                    "--output-dir", str(model_root),
                    "--force",
                ],
                timeout_seconds=max(1800, int(timeout_seconds)),
            )

        log = _run_checked(
            [
                sys.executable,
                "-m", "mel_band_roformer.inference",
                "--model", entry.slug,
                "--models_dir", str(model_root),
                "--input_folder", str(input_dir),
                "--store_dir", str(output_dir),
                "--device", device,
            ],
            timeout_seconds=max(1800, int(timeout_seconds)),
        )

        lead = _find_output(output_dir, "vocals")
        backing = _find_output(output_dir, "instrumental")

        shutil.copy2(lead, payload_dir / "lead_vocals.wav")
        shutil.copy2(backing, payload_dir / "backing_vocals.wav")

        manifest = {
            "schema_version": 2,
            "engine": "melband-roformer-karaoke-lead-backing-v1",
            "model": entry.slug,
            "audio_hash": str(audio_hash),
            "source": str(vocals_path),
            "timebase": "original_audio_seconds",
            "device": device,
            "model_cache": str(model_root),
            "stems": {
                "lead_vocals": "lead_vocals.wav",
                "backing_vocals": "backing_vocals.wav",
            },
        }
        (payload_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if target.exists():
            shutil.rmtree(target)
        payload_dir.replace(target)

        return {
            "status": "generated",
            "model": entry.slug,
            "paths": vocal_stem_paths(audio_hash),
            "log_tail": "\n".join(log.splitlines()[-40:]),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)
