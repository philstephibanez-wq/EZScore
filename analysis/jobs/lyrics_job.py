from __future__ import annotations

from pathlib import Path

from ._process import python_executable, run_passthrough


def run(job: dict, root: Path) -> int:
    paths = job.get("paths") or {}
    request = job.get("request") or {}

    mode = str(request.get("mode") or "align").strip().lower()
    if mode not in {"extract", "align"}:
        raise RuntimeError(f"lyrics_job_invalid_mode:{mode}")

    if mode == "align":
        audio = paths.get("source")
    else:
        audio = paths.get("lead_vocals") or paths.get("source")

    if not audio:
        raise RuntimeError("lyrics_audio_source_missing")

    result_file = paths.get("result_file")
    progress_file = paths.get("progress_file")
    if not result_file or not progress_file:
        raise RuntimeError("lyrics_job_paths_missing")

    command = [
        python_executable(),
        str(root / "analysis" / "lyrics_timeline_analysis.py"),
        "--audio", str(audio),
        "--output", str(result_file),
        "--progress-file", str(progress_file),
        "--mode", mode,
    ]

    if mode == "align":
        vocal_audio = paths.get("lead_vocals")
        if vocal_audio:
            command += ["--vocal-audio", str(vocal_audio)]

        lyrics_file = paths.get("lyrics_file")
        if not lyrics_file:
            raise RuntimeError("lyrics_file_missing")
        command += ["--lyrics-file", str(lyrics_file)]

    return run_passthrough(command, cwd=root)
