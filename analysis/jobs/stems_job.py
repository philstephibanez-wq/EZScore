from __future__ import annotations

import os
from pathlib import Path

from ._process import python_executable, run_passthrough


def run(job: dict, root: Path) -> int:
    paths = job.get("paths") or {}
    request = job.get("request") or {}

    required = ("source", "storage_root", "progress_file")
    missing = [name for name in required if not paths.get(name)]
    if missing:
        raise RuntimeError("stems_job_missing_paths:" + ",".join(missing))

    command = [
        python_executable(),
        str(root / "analysis" / "stems_only.py"),
        "--source", str(paths["source"]),
        "--audio-hash", str(request.get("audio_sha256") or ""),
        "--storage-root", str(paths["storage_root"]),
        "--progress-file", str(paths["progress_file"]),
    ]
    if bool(request.get("force")):
        command.append("--force")

    env = {
        "BS_ROFORMER_MODELS_PATH": os.environ.get(
            "BS_ROFORMER_MODELS_PATH", r"H:\EZScoreModels\bs-roformer"
        ),
        "MELBAND_ROFORMER_MODELS_PATH": os.environ.get(
            "MELBAND_ROFORMER_MODELS_PATH", r"H:\EZScoreModels\melband-roformer"
        ),
        "EZSCORE_RUNTIME_TMP": os.environ.get(
            "EZSCORE_RUNTIME_TMP", r"H:\Temp\EZScore"
        ),
        "EZSCORE_STEM_DEVICE": os.environ.get("EZSCORE_STEM_DEVICE", "cuda:0"),
    }

    rc = run_passthrough(command, cwd=root, env=env)
    if rc != 0:
        return rc

    proxy_builder = root / "analysis" / "build_playback_proxies.py"
    if not proxy_builder.is_file():
        raise RuntimeError("playback_proxy_builder_missing")

    proxy_command = [
        python_executable(),
        str(proxy_builder),
        "--source", str(paths["source"]),
        "--storage-root", str(paths["storage_root"]),
        "--progress-file", str(paths["progress_file"]),
    ]
    return run_passthrough(proxy_command, cwd=root, env=env)
