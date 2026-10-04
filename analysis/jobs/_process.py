from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

WINDOWS_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_passthrough(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    process_env["PYTHONUTF8"] = "1"
    process_env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=process_env,
        stdout=None,
        stderr=None,
        creationflags=WINDOWS_NO_WINDOW if os.name == "nt" else 0,
    )
    return int(proc.wait())


def python_executable() -> str:
    return sys.executable
