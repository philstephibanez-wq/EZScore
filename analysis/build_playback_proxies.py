#!/usr/bin/env python3
"""Build lightweight high-quality Opus proxies for the EZScore multipiste player.

The WAV stems remain untouched and continue to be the analytical masters.
This script creates playback-only sidecars for the current immutable STEM run.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACKS = (
    "original",
"lead_vocals",
    "backing_vocals",
    "drums",
    "bass",
    "guitar",
    "piano",
    "other",
)

STEMS = TRACKS[1:]
OPUS_BITRATE = "192k"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    delay = 0.02
    try:
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                return
            except (PermissionError, OSError):
                if attempt >= 7:
                    raise
                time.sleep(delay)
                delay = min(delay * 2.0, 0.25)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _progress(path: Path | None, track: str, index: int, total: int) -> None:
    if path is None:
        return
    engine_percent = round((index / max(1, total)) * 100)
    overall_percent = 92 + round((7 * index) / max(1, total))
    _write_json(path, {
        "percent": min(99, overall_percent),
        "stage": "playback",
        "message": f"Optimizing playback audio: {track}.",
        "engine_percent": engine_percent,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def _log_perf(log_path: Path, phase: str, seconds: float, **extra: object) -> None:
    details = " ".join(f"{key}={value}" for key, value in extra.items())
    suffix = f" {details}" if details else ""
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n[PERF] phase={phase} duration_seconds={seconds:.3f}{suffix}\n")


def _ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg is required to build Opus playback proxies.")
    return executable


def _read_current_run(storage_root: Path) -> tuple[str, Path]:
    pointer = storage_root / "current.json"
    if not pointer.is_file():
        raise RuntimeError("Current STEM run pointer is missing.")

    payload = json.loads(pointer.read_text(encoding="utf-8"))
    run = str(payload.get("run", "")).strip()

    if not run.startswith("run-") or not run.replace("-", "").isalnum():
        raise RuntimeError("Invalid current STEM run pointer.")

    run_dir = storage_root / "runs" / run
    if not run_dir.is_dir():
        raise RuntimeError(f"Current STEM run does not exist: {run}")

    return run, run_dir


def _encode(source: Path, target: Path, *, log_path: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    command = [
        _ffmpeg(),
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(source),
        "-vn",
        "-map_metadata", "-1",
        "-ar", "48000",
        "-c:a", "libopus",
        "-b:a", OPUS_BITRATE,
        "-vbr", "on",
        "-compression_level", "10",
        "-application", "audio",
        "-frame_duration", "20",
        str(target),
    ]

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(
            f"\n[{datetime.now(timezone.utc).isoformat()}] "
            f"Playback proxy: {source.name} -> {target.name}\n"
        )
        log.flush()

        result = subprocess.run(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            check=False,
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg Opus proxy failed for {source.name} "
            f"with exit code {result.returncode}."
        )

    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError(f"Invalid Opus proxy produced: {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--progress-file")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    storage_root = Path(args.storage_root).resolve()
    progress_file = (
        Path(args.progress_file).resolve()
        if args.progress_file
        else None
    )

    if not source.is_file() or source.stat().st_size <= 0:
        raise RuntimeError(f"Invalid original audio source: {source}")

    run_name, run_dir = _read_current_run(storage_root)

    playback_root = storage_root / "playback"
    target_dir = playback_root / run_name
    log_path = storage_root / "worker.log"

    # Fast cache path.
    manifest_path = target_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            complete = all(
                (target_dir / f"{track}.opus").is_file()
                and (target_dir / f"{track}.opus").stat().st_size > 0
                for track in TRACKS
            )
            if (
                complete
                and manifest.get("schema_version") == 1
                and manifest.get("codec") == "opus"
                and manifest.get("source_run") == run_name
            ):
                _progress(progress_file, "cached", len(TRACKS), len(TRACKS))
                return 0
        except Exception:
            pass

    playback_root.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f"{run_name}-playback-",
            dir=str(playback_root),
        )
    )

    playback_started = time.monotonic()
    try:
        sources: dict[str, Path] = {"original": source}
        for stem in STEMS:
            stem_path = run_dir / f"{stem}.wav"
            if not stem_path.is_file() or stem_path.stat().st_size <= 0:
                raise RuntimeError(f"Missing analytical STEM WAV: {stem}")
            sources[stem] = stem_path

        artifacts: dict[str, dict] = {}

        for index, track in enumerate(TRACKS, start=1):
            _progress(progress_file, track, index - 1, len(TRACKS))
            source_path = sources[track]
            target = staging / f"{track}.opus"

            track_started = time.monotonic()
            _encode(source_path, target, log_path=log_path)
            _log_perf(log_path, "opus_track", time.monotonic() - track_started, track=track, bytes=target.stat().st_size)

            artifacts[track] = {
                "file": f"{track}.opus",
                "bytes": target.stat().st_size,
                "source": (
                    "original_audio"
                    if track == "original"
                    else f"{track}.wav"
                ),
            }
            _progress(progress_file, track, index, len(TRACKS))

        manifest = {
            "schema_version": 1,
            "purpose": "realtime_multitrack_playback",
            "source_run": run_name,
            "codec": "opus",
            "container": "ogg",
            "bitrate": OPUS_BITRATE,
            "sample_rate": 48000,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tracks": artifacts,
        }
        _write_json(staging / "manifest.json", manifest)

        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        staging.replace(target_dir)
        staging = None

        _log_perf(log_path, "playback_total", time.monotonic() - playback_started)
        if progress_file is not None:
            _write_json(progress_file, {"percent": 100, "stage": "complete", "message": "STEMS and playback audio ready.", "engine_percent": 100, "updated_at": datetime.now(timezone.utc).isoformat()})
        return 0
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
