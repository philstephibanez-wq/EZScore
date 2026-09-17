from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Optional

import numpy as np
import soundfile as sf


SUPPORTED_INPUT_EXTENSIONS = {
    ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".wma",
}


@dataclass(frozen=True)
class SeparationResult:
    engine: str
    working_dir: str
    analysis_source_path: str
    harmonic_path: str
    stems: Dict[str, str]


def bs_roformer_disponible() -> bool:
    try:
        return importlib.util.find_spec("bs_roformer") is not None
    except Exception:
        return False


def demucs_disponible() -> bool:
    try:
        return importlib.util.find_spec("demucs") is not None
    except Exception:
        return False


def _temp_root() -> Path:
    configured = str(os.environ.get("EZSCORE_TEMP_DIR", "") or "").strip()
    if configured:
        root = Path(configured).expanduser()
    elif os.name == "nt" and Path("H:/Temp").exists():
        root = Path("H:/Temp/EZScore")
    else:
        root = Path(tempfile.gettempdir()) / "EZScore"

    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_extension(extension: Optional[str]) -> str:
    raw = str(extension or ".wav").strip().lower()
    if not raw.startswith("."):
        raw = "." + raw
    if raw not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError(
            f"Format audio non pris en charge : {raw}. "
            f"Formats acceptés : {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}"
        )
    return raw


def _ffmpeg_executable() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError(
            "FFmpeg est introuvable dans PATH. "
            "Il est requis pour normaliser MP3/FLAC/M4A/OGG/etc."
        )
    return executable


def _normaliser_vers_wav(source_path: Path, wav_path: Path) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_executable(),
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source_path),
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not wav_path.exists():
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Échec de normalisation audio FFmpeg : "
            + (details[-2000:] if details else "erreur inconnue")
        )


def _run_command(cmd: list[str], label: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"Échec {label} : "
            + (details[-3000:] if details else "erreur inconnue")
        )


def _find_stem(output_dir: Path, stem_name: str) -> Optional[Path]:
    wanted = stem_name.lower()

    for path in output_dir.rglob("*.wav"):
        if path.stem.lower() == wanted:
            return path

    for path in output_dir.rglob("*.wav"):
        stem = path.stem.lower()
        if (
            stem.endswith("_" + wanted)
            or stem.endswith("-" + wanted)
            or stem.startswith(wanted + "_")
            or stem.startswith(wanted + "-")
        ):
            return path
    return None


def _build_harmonic_mix(stems: Dict[str, Path], destination: Path) -> None:
    # vocals et drums sont exclus. La basse reste pondérée pour fournir
    # la fondamentale sans écraser l'information majeur/mineur.
    weights = {
        "guitar": 1.00,
        "piano": 1.00,
        "other": 0.80,
        "bass": 0.65,
    }

    tracks = []
    sample_rate = None
    min_frames = None

    for name, weight in weights.items():
        path = stems.get(name)
        if path is None:
            continue

        audio, sr = sf.read(str(path), dtype="float32", always_2d=True)

        if sample_rate is None:
            sample_rate = int(sr)
        elif int(sr) != sample_rate:
            raise RuntimeError(
                f"Sample rates BS-RoFormer incohérents : {sample_rate} / {sr}."
            )

        min_frames = len(audio) if min_frames is None else min(min_frames, len(audio))
        tracks.append((audio, float(weight), name))

    if not tracks or sample_rate is None or min_frames is None:
        raise RuntimeError(
            "BS-RoFormer n'a produit aucun stem harmonique exploitable "
            "(guitar/piano/other/bass)."
        )

    mix = np.zeros((min_frames, 2), dtype=np.float32)
    total_weight = 0.0

    for audio, weight, _name in tracks:
        audio = audio[:min_frames]
        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        elif audio.shape[1] > 2:
            audio = audio[:, :2]

        mix += audio.astype(np.float32, copy=False) * weight
        total_weight += weight

    mix /= max(total_weight, 1e-12)

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.98:
        mix *= (0.98 / peak)

    sf.write(str(destination), mix, sample_rate, subtype="PCM_16")


def _separer_bs_roformer(
    normalized_wav: Path,
    workdir: Path,
    device: str,
) -> SeparationResult:
    input_dir = workdir / "bs_input"
    output_dir = workdir / "bs_output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    roformer_input = input_dir / "input.wav"
    shutil.copy2(normalized_wav, roformer_input)

    cmd = [
        sys.executable,
        "-m",
        "bs_roformer.inference",
        "--input_folder", str(input_dir),
        "--store_dir", str(output_dir),
        "--device", str(device),
    ]
    _run_command(cmd, "BS-RoFormer")

    stems: Dict[str, Path] = {}
    for stem_name in ("vocals", "drums", "bass", "guitar", "piano", "other"):
        path = _find_stem(output_dir, stem_name)
        if path is not None:
            stems[stem_name] = path

    harmonic_path = workdir / "harmonic_bs_roformer.wav"
    _build_harmonic_mix(stems, harmonic_path)

    return SeparationResult(
        engine="bs_roformer",
        working_dir=str(workdir),
        analysis_source_path=str(normalized_wav),
        harmonic_path=str(harmonic_path),
        stems={name: str(path) for name, path in stems.items()},
    )


def _separer_demucs(
    normalized_wav: Path,
    workdir: Path,
    device: str,
) -> SeparationResult:
    output_dir = workdir / "demucs_output"
    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "--two-stems=vocals",
        "-n",
        "htdemucs",
        "-o",
        str(output_dir),
        str(normalized_wav),
    ]
    _ = device
    _run_command(cmd, "Demucs")

    candidates = list(output_dir.rglob("no_vocals.wav"))
    if not candidates:
        raise RuntimeError("no_vocals.wav introuvable après Demucs.")

    return SeparationResult(
        engine="demucs",
        working_dir=str(workdir),
        analysis_source_path=str(normalized_wav),
        harmonic_path=str(candidates[0]),
        stems={"no_vocals": str(candidates[0])},
    )


def separer_audio_harmonique(
    audio_bytes: bytes,
    extension: Optional[str],
    device: str = "cuda",
) -> SeparationResult:
    """
    Entrée publique EZScore.
    Multi-format -> WAV temporaire -> BS-RoFormer ; Demucs en secours.
    """
    ext = _safe_extension(extension)
    workdir = Path(
        tempfile.mkdtemp(prefix="ezscore_audio_", dir=str(_temp_root()))
    )

    try:
        source_path = workdir / f"source{ext}"
        source_path.write_bytes(audio_bytes)

        normalized_wav = workdir / "source_normalized.wav"
        _normaliser_vers_wav(source_path, normalized_wav)

        if bs_roformer_disponible():
            return _separer_bs_roformer(normalized_wav, workdir, device)

        if demucs_disponible():
            return _separer_demucs(normalized_wav, workdir, device)

        raise RuntimeError(
            "Aucun moteur de séparation audio disponible. "
            "Installer bs-roformer-infer (recommandé) ou Demucs."
        )

    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


def nettoyer_separation(result: Optional[SeparationResult]) -> None:
    if result is None:
        return
    working_dir = str(result.working_dir or "").strip()
    if working_dir:
        shutil.rmtree(working_dir, ignore_errors=True)
