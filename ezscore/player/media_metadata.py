from __future__ import annotations

"""Server-side media metadata for browser-independent seeker initialization."""

from functools import lru_cache
from pathlib import Path
import shutil
import subprocess


@lru_cache(maxsize=256)
def _duration_cached(path_text: str, size: int, mtime_ns: int) -> float:
    path = Path(path_text)
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0

    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=12,
    )
    if result.returncode != 0:
        return 0.0
    try:
        value = float((result.stdout or "").strip())
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0.0 else 0.0


def duration_seconds(path: Path) -> float:
    media = Path(path)
    try:
        stat = media.stat()
    except OSError:
        return 0.0
    return _duration_cached(
        str(media.resolve()),
        int(stat.st_size),
        int(stat.st_mtime_ns),
    )
