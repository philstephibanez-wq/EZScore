from __future__ import annotations

from pathlib import Path

from ._process import python_executable, run_passthrough


def run(job: dict, root: Path) -> int:
    paths = job.get("paths") or {}
    request = job.get("request") or {}

    required = ("source", "progress_file", "result_file")
    missing = [name for name in required if not paths.get(name)]
    if missing:
        raise RuntimeError("chords_job_missing_paths:" + ",".join(missing))

    command = [
        python_executable(),
        str(root / "analysis" / "chord_timeline_analysis.py"),
        "--audio", str(paths["source"]),
        "--level", str(request.get("level") or "intermediate"),
        "--time-signature", str(request.get("time_signature") or "auto"),
        "--progress-file", str(paths["progress_file"]),
        "--output", str(paths["result_file"]),
    ]

    for stem_path in (paths.get("harmony_stems") or []):
        if stem_path:
            command.extend(["--stem", str(stem_path)])

    if paths.get("drums"):
        command.extend(["--drums", str(paths["drums"])])

    if bool(request.get("filter_noise")):
        command.append("--filter-noise")

    return run_passthrough(command, cwd=root)
