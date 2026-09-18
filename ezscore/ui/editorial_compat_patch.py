from __future__ import annotations

"""Compatibility recovery for editorial fingerprints after technical changes.

This module preserves the strict "no automatic remapping" rule.

Two cases are handled:

1. Known semantic migration:
   the old provisional "Chœurs" lane was produced only because the second
   Whisper pass found words omitted by the mix pass. Those recovered words are
   now correctly considered lead-vocal recovery, not evidence of backing vocals.
   When that is the ONLY fingerprint difference, lead/chord edits, line breaks
   and anchors are preserved. Obsolete backing-vocal overrides are discarded.

2. Any real technical timeline change:
   no remapping is attempted. The incompatible editorial file is archived
   atomically and the current timeline starts from a clean editorial payload.
   The old file remains recoverable on disk.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.ui import editorial_timeline as _timeline
from ezscore.ui import lyrics_inline_editor as _editor


_MISMATCH = (
    "La timeline technique a changé depuis la sauvegarde éditoriale. "
    "Aucun remapping automatique."
)


def _clean_word(word: dict[str, Any]) -> dict[str, Any] | None:
    text = str(word.get("text", "") or "").strip()
    if not text:
        return None

    start = float(word.get("start", 0.0) or 0.0)
    end = float(word.get("end", start) or start)
    confidence = float(word.get("confidence", 1.0) or 0.0)

    if end < start:
        return None

    return {
        "start": start,
        "end": end,
        "text": text,
        "confidence": confidence,
    }


def _legacy_merge_vocal_gap_words(
    original_words: list[dict[str, Any]],
    vocal_words: list[dict[str, Any]],
    *,
    min_gap: float = 1.10,
    edge_guard: float = 0.32,
) -> list[dict[str, Any]]:
    """Exact historical gap-supplement semantics used before the choir fix."""
    original = sorted(
        [
            cleaned
            for cleaned in (_clean_word(w) for w in original_words)
            if cleaned is not None
        ],
        key=lambda w: (w["start"], w["end"]),
    )
    vocal = sorted(
        [
            cleaned
            for cleaned in (_clean_word(w) for w in vocal_words)
            if cleaned is not None and cleaned["confidence"] >= 0.30
        ],
        key=lambda w: (w["start"], w["end"]),
    )

    if not original:
        return [
            {"start": w["start"], "end": w["end"], "text": w["text"]}
            for w in vocal
        ]
    if not vocal:
        return [
            {"start": w["start"], "end": w["end"], "text": w["text"]}
            for w in original
        ]

    gaps: list[tuple[float, float]] = []

    first_start = float(original[0]["start"])
    if first_start >= min_gap:
        gaps.append((0.0, max(0.0, first_start - edge_guard)))

    for left, right in zip(original, original[1:]):
        gap_start = float(left["end"])
        gap_end = float(right["start"])
        if gap_end - gap_start >= min_gap:
            gaps.append(
                (gap_start + edge_guard, gap_end - edge_guard)
            )

    last_end = float(original[-1]["end"])
    gaps.append((last_end + edge_guard, float("inf")))

    additions: list[dict[str, Any]] = []
    for word in vocal:
        center = (float(word["start"]) + float(word["end"])) / 2.0
        if any(g0 <= center <= g1 for g0, g1 in gaps):
            additions.append(
                {
                    "start": float(word["start"]),
                    "end": float(word["end"]),
                    "text": str(word["text"]),
                }
            )

    return sorted(
        [
            {
                "start": float(w["start"]),
                "end": float(w["end"]),
                "text": str(w["text"]),
            }
            for w in original
        ] + additions,
        key=lambda w: (w["start"], w["end"]),
    )


def _legacy_supplement_only_words(
    original_words: list[dict[str, Any]],
    merged_words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exact historical rule that incorrectly labelled supplements as choir."""
    original = [
        {
            "start": float(w.get("start", 0.0) or 0.0),
            "end": float(
                w.get("end", w.get("start", 0.0)) or 0.0
            ),
            "text": str(w.get("text", "") or "").strip(),
        }
        for w in original_words
        if str(w.get("text", "") or "").strip()
    ]

    additions: list[dict[str, Any]] = []

    for word in merged_words:
        text_value = str(word.get("text", "") or "").strip()
        if not text_value:
            continue

        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        center = (start + end) / 2.0

        matched = False
        for ref in original:
            if ref["start"] - 0.18 <= center <= ref["end"] + 0.18:
                matched = True
                break

        if not matched:
            additions.append(
                {"start": start, "end": end, "text": text_value}
            )

    return additions


def _legacy_backing_words(
    work_dir: Path,
    lead_words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cache = Path(work_dir) / "whisper_vocals_small.json"
    if not cache.is_file():
        return []

    payload = json.loads(cache.read_text(encoding="utf-8"))
    merged = _legacy_merge_vocal_gap_words(
        lead_words,
        list(payload.get("words", []) or []),
    )
    supplement = _legacy_supplement_only_words(
        lead_words,
        merged,
    )
    return _timeline.normalize_words(supplement)


def _try_false_choir_migration(
    original_load,
    *,
    work_dir: Path,
    lead_words,
    backing_words,
    beats,
):
    # New semantics: ordinary second-pass recovery no longer populates backing.
    if backing_words:
        return None

    legacy_backing = _legacy_backing_words(
        work_dir,
        list(lead_words or []),
    )
    if not legacy_backing:
        return None

    # This call succeeds only if the stored fingerprint exactly matches the
    # previous technical inputs. Therefore no lead/chord/beat remapping occurs.
    legacy_payload = original_load(
        work_dir,
        lead_words,
        legacy_backing,
        beats,
    )

    migrated = dict(legacy_payload)
    migrated["backing_overrides"] = {}

    clean = _timeline.save(
        work_dir,
        migrated,
        lead_words,
        backing_words,
        beats,
    )

    st.info(
        "Ancienne lane « Chœurs » provisoire migrée : les mots récupérés "
        "restent dans Chant. Corrections Chant/Accords, ↵ et ancres conservés."
    )
    return clean


def _archive_stale_editorial(work_dir: Path) -> Path | None:
    source = _timeline.path_for(work_dir)
    if not source.is_file():
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = source.with_name(
        f"{source.stem}.stale-{stamp}{source.suffix}"
    )

    counter = 1
    while target.exists():
        target = source.with_name(
            f"{source.stem}.stale-{stamp}-{counter}{source.suffix}"
        )
        counter += 1

    source.replace(target)
    return target


def install() -> None:
    """Patch only the editor's imported load function, once."""
    original_load = _editor.load_editorial

    if getattr(original_load, "_ezscore_editorial_recovery_patch", False):
        return

    def load_with_recovery(
        work_dir: Path,
        lead_words,
        backing_words,
        beats,
    ):
        try:
            return original_load(
                work_dir,
                lead_words,
                backing_words,
                beats,
            )
        except RuntimeError as exc:
            if str(exc) != _MISMATCH:
                raise

        # First try the one deterministic semantic migration introduced by the
        # choir correction. It is accepted only if the OLD fingerprint matches
        # exactly when reconstructed.
        try:
            migrated = _try_false_choir_migration(
                original_load,
                work_dir=Path(work_dir),
                lead_words=lead_words,
                backing_words=backing_words,
                beats=beats,
            )
        except Exception:
            migrated = None

        if migrated is not None:
            return migrated

        # Real timeline change: strict behavior remains. Archive, do not remap.
        archived = _archive_stale_editorial(Path(work_dir))
        fresh = _timeline.empty_payload(
            lead_words,
            backing_words,
            beats,
        )

        if archived is not None:
            st.warning(
                "La timeline technique a réellement changé. "
                "Aucun remapping automatique : l'ancienne édition a été "
                f"archivée sous {archived.name}. La nouvelle timeline repart "
                "avec une édition vierge."
            )
        else:
            st.warning(
                "La timeline technique a réellement changé. "
                "Aucun remapping automatique ; nouvelle édition vierge."
            )

        return fresh

    load_with_recovery._ezscore_editorial_recovery_patch = True
    _editor.load_editorial = load_with_recovery
