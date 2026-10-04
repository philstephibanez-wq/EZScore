from __future__ import annotations

from pathlib import Path

from . import stems_job, chords_job, lyrics_job

_HANDLERS = {
    "stems": stems_job.run,
    "chords": chords_job.run,
    "lyrics": lyrics_job.run,
}


def dispatch_job(job: dict, root: Path) -> int:
    kind = str(job.get("kind") or "").strip().lower()
    try:
        handler = _HANDLERS[kind]
    except KeyError as exc:
        raise RuntimeError(f"unsupported_job_kind:{kind or '<empty>'}") from exc
    return int(handler(job, root))
