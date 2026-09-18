from __future__ import annotations

"""Read-only STEM player adapter.

Contract:
- consumes persisted Analyse artifacts only;
- never launches Whisper;
- never launches beat/chord analysis;
- never mutates technical caches;
- never exposes re-analysis actions;
- never infers backing vocals.

Re-analysis belongs to the Analyse surface, not to the player.
"""

from pathlib import Path
from typing import Any

from ezscore.analysis import technical_snapshot
from ezscore.player import karaoke_stem_webaudio as base
from ezscore.player import karaoke_stem_webaudio_r12c as r12c


def _tracks(
    source: Path,
    stems: dict[str, Path],
    preview_dir: Path,
    key: str,
) -> list[dict[str, Any]]:
    previews = base.prepare_browser_previews(source, stems, preview_dir)
    tracks: list[dict[str, Any]] = []

    def pack(
        name: str,
        label: str,
        *,
        enabled: bool,
        volume: float,
    ) -> None:
        preview = previews[name]
        tracks.append(
            {
                "name": name,
                "label": label,
                "url": base.register_media_url(
                    preview,
                    coordinates=f"{key}:truth:{name}",
                    mimetype="audio/mpeg",
                ),
                "enabled": enabled,
                "volume": volume,
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
            }
        )

    pack("original", "Original", enabled=True, volume=1.0)

    labels = {
        "vocals": "Chant",
        "drums": "Batterie",
        "bass": "Basse",
        "other": "Other",
    }
    defaults = {
        "vocals": 0.90,
        "drums": 0.75,
        "bass": 0.75,
        "other": 0.75,
    }

    for name in base.STEM_NAMES:
        if name in stems and name in previews:
            pack(
                name,
                labels.get(name, name.title()),
                enabled=False,
                volume=defaults.get(name, 0.75),
            )

    return tracks


def render_player(
    source: Path,
    stems: dict[str, Path],
    *,
    preview_dir: Path,
    key: str,
    words: list[dict[str, Any]] | None = None,
) -> None:
    """Render the persisted technical snapshot; computation is forbidden."""
    source = Path(source)
    preview_dir = Path(preview_dir)
    work_dir = preview_dir.parent
    audio_hash = work_dir.name
    storage_key = str(key)

    r12c._AUDIO_HASH_BY_STORAGE_KEY[storage_key] = audio_hash
    r12c._PREVIEW_DIR_BY_STORAGE_KEY[storage_key] = preview_dir

    lead_words = list(words or [])
    beats = technical_snapshot.beats(work_dir)
    backing_words = technical_snapshot.explicit_backing_words(work_dir)

    payload = {
        "tracks": _tracks(source, stems, preview_dir, storage_key),
        "words": lead_words,
        "lead_words": lead_words,
        "backing_words": backing_words,
        "beats": beats,
        "meter_default": technical_snapshot.meter_default(work_dir),
        "storage_key": storage_key,
    }

    # Diagram generation is presentation derived from already persisted chords.
    try:
        payload["chord_diagrams"] = r12c._build_chord_diagrams(
            audio_hash,
            beats,
        )
    except Exception:
        payload["chord_diagrams"] = {}

    try:
        payload["show_diagrams_default"] = bool(
            r12c.load_show_diagrams(audio_hash)
        )
    except Exception:
        payload["show_diagrams_default"] = False

    r12c._COMPONENT_R12C(
        data=payload,
        key=storage_key,
        width="stretch",
        height=900 if lead_words else 620,
    )
