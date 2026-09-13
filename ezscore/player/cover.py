"""Cover-art helpers shared by editor preview and front player."""

from __future__ import annotations

import base64
from pathlib import Path


_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def cover_payload(path) -> dict[str, str]:
    """Return a browser-ready cover payload, or an empty payload."""
    if not path:
        return {}
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    suffix = candidate.suffix.lower()
    mime = _MIME.get(suffix)
    if mime is None:
        return {}
    return {
        "mime": mime,
        "base64": base64.b64encode(candidate.read_bytes()).decode("ascii"),
    }
