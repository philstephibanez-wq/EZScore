"""Canonical editorial overlay for EZScore.

Technical timelines remain immutable. This module persists only editorial
overlays used later by the final player and printing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for word in words or []:
        text = str(word.get("text", "") or "").strip()
        if not text:
            continue
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        if end < start:
            raise RuntimeError("Timeline mot invalide : fin < début.")
        result.append(
            {
                "index": len(result),
                "text": text,
                "start": start,
                "end": end,
            }
        )
    return result


def _first_timing_value(
    beat: dict[str, Any],
    keys: tuple[str, ...],
) -> tuple[float | None, str]:
    """Return the first explicitly present timing value, including zero."""
    for key in keys:
        if key not in beat:
            continue
        value = beat.get(key)
        if value is None:
            continue
        try:
            return float(value), key
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Timeline beat invalide : {key}={value!r}."
            ) from exc
    return None, ""


def normalize_beats(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize historical and canonical beat schemas without moving beats.

    Historical EZScore beat payloads use ``start`` / ``temps`` / ``time_start``.
    The current HQ structure pipeline stores the canonical beat point in
    ``beat_timeline[].time``.

    R5.10 originally forgot that last key. On a modern structure every beat was
    therefore normalized to t=0 and all chord boxes stacked at the left edge.

    Compatibility rule:
    - existing historical schemas keep their exact previous normalization;
    - only the canonical ``time`` schema receives the missing mapping;
    - for that point-based schema, the end of a beat is the next canonical
      beat point (last beat uses the preceding positive interval).

    Private ``_legacy_*`` fields are carried only in memory so ``load()`` can
    recognize the exact R5.10 zero-time fingerprint and preserve editorial
    overlays already saved while the bug was active. They are never persisted.
    """
    source = list(beats or [])
    staged: list[dict[str, Any]] = []

    for index, beat in enumerate(source):
        if not isinstance(beat, dict):
            raise RuntimeError(
                f"Timeline beat invalide à l'index {index} : objet attendu."
            )

        # Exact pre-fix R5.10 normalization, retained only for deterministic
        # fingerprint migration.
        legacy_start = float(
            beat.get(
                "start",
                beat.get("temps", beat.get("time_start", 0.0)),
            )
            or 0.0
        )
        legacy_end = float(
            beat.get(
                "end",
                beat.get("fin", beat.get("time_end", legacy_start)),
            )
            or legacy_start
        )

        start_value, start_key = _first_timing_value(
            beat,
            ("start", "temps", "time_start", "time"),
        )
        start = float(start_value if start_value is not None else 0.0)

        end_value, end_key = _first_timing_value(
            beat,
            ("end", "fin", "time_end"),
        )

        chord = str(
            beat.get("chord", beat.get("accord", beat.get("label", "."))) or "."
        ).strip() or "."

        staged.append(
            {
                "index": index,
                "start": start,
                "_start_key": start_key,
                "_explicit_end": end_value,
                "_end_key": end_key,
                "chord": chord,
                "_legacy_start": legacy_start,
                "_legacy_end": legacy_end,
            }
        )

    # Positive canonical-time intervals are used only for the final point of a
    # modern ``time`` timeline. They do not alter old schemas.
    time_starts = [
        float(item["start"])
        for item in staged
        if item["_start_key"] == "time"
    ]
    positive_intervals = [
        b - a
        for a, b in zip(time_starts, time_starts[1:])
        if b - a > 1e-9
    ]
    last_interval = (
        positive_intervals[-1]
        if positive_intervals
        else 0.0
    )

    result: list[dict[str, Any]] = []
    for index, item in enumerate(staged):
        start = float(item["start"])
        explicit_end = item["_explicit_end"]

        if explicit_end is not None:
            end = float(explicit_end)
        elif item["_start_key"] == "time":
            next_start = None
            if index + 1 < len(staged):
                candidate = float(staged[index + 1]["start"])
                if candidate > start:
                    next_start = candidate
            end = (
                next_start
                if next_start is not None
                else start + last_interval
            )
        else:
            # Preserve R5.10 behavior for historical schemas.
            end = start

        if end < start:
            raise RuntimeError(f"Timeline beat invalide à l'index {index}.")

        normalized = {
            "index": index,
            "start": start,
            "end": end,
            "chord": str(item["chord"]),
        }

        legacy_start = float(item["_legacy_start"])
        legacy_end = float(item["_legacy_end"])
        if (
            round(legacy_start, 9) != round(start, 9)
            or round(legacy_end, 9) != round(end, 9)
        ):
            normalized["_legacy_start"] = legacy_start
            normalized["_legacy_end"] = legacy_end

        result.append(normalized)

    return result


def fingerprint(lead_words, backing_words, beats) -> str:
    compact = {
        "lead": [
            [w["text"], round(float(w["start"]), 5), round(float(w["end"]), 5)]
            for w in lead_words
        ],
        "backing": [
            [w["text"], round(float(w["start"]), 5), round(float(w["end"]), 5)]
            for w in backing_words
        ],
        "beats": [
            [b["chord"], round(float(b["start"]), 5), round(float(b["end"]), 5)]
            for b in beats
        ],
    }
    raw = json.dumps(
        compact,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _legacy_r5_10_fingerprint(
    lead_words,
    backing_words,
    beats,
) -> str | None:
    """Rebuild only the exact fingerprint produced by the known time-key bug."""
    if not any("_legacy_start" in beat for beat in beats):
        return None

    legacy_beats = []
    for index, beat in enumerate(beats):
        legacy_beats.append(
            {
                "index": index,
                "start": float(beat.get("_legacy_start", beat["start"])),
                "end": float(beat.get("_legacy_end", beat["end"])),
                "chord": str(beat["chord"]),
            }
        )

    return fingerprint(lead_words, backing_words, legacy_beats)


def path_for(work_dir: Path) -> Path:
    return Path(work_dir) / "editorial_timeline.json"


def empty_payload(lead_words, backing_words, beats) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_fingerprint": fingerprint(lead_words, backing_words, beats),
        "lead_overrides": {},
        "backing_overrides": {},
        "line_break_after_lead": [],
        "chord_overrides": {},
        "anchors": [],
        "updated_at": "",
    }


def _validate_overrides(
    name: str,
    raw: Any,
    size: int,
) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise RuntimeError(f"{name}: format invalide.")

    clean: dict[str, str] = {}
    for key, value in raw.items():
        index = int(key)
        if index < 0 or index >= size:
            raise RuntimeError(f"{name}: index {index} hors plage.")
        text = str(value or "").strip()
        if not text:
            raise RuntimeError(f"{name}: valeur vide à l'index {index}.")
        clean[str(index)] = text
    return clean


def validate(payload, lead_words, backing_words, beats) -> dict[str, Any]:
    if int(payload.get("schema_version", 0) or 0) != SCHEMA_VERSION:
        raise RuntimeError(
            "Version éditoriale incompatible. Aucune conversion silencieuse."
        )

    expected = fingerprint(lead_words, backing_words, beats)
    if str(payload.get("source_fingerprint", "") or "") != expected:
        raise RuntimeError(
            "La timeline technique a changé depuis la sauvegarde éditoriale. "
            "Aucun remapping automatique."
        )

    lead_overrides = _validate_overrides(
        "lead_overrides",
        payload.get("lead_overrides", {}),
        len(lead_words),
    )
    backing_overrides = _validate_overrides(
        "backing_overrides",
        payload.get("backing_overrides", {}),
        len(backing_words),
    )
    chord_overrides = _validate_overrides(
        "chord_overrides",
        payload.get("chord_overrides", {}),
        len(beats),
    )

    line_breaks = sorted(
        set(int(value) for value in payload.get("line_break_after_lead", []))
    )
    for index in line_breaks:
        if index < 0 or index >= max(0, len(lead_words) - 1):
            raise RuntimeError(f"Saut de ligne hors plage après le mot {index}.")

    anchors_raw = payload.get("anchors", [])
    if not isinstance(anchors_raw, list):
        raise RuntimeError("anchors: format invalide.")

    anchors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in anchors_raw:
        anchor_id = str(raw.get("id", "") or "").strip()
        label = str(raw.get("label", "") or "").strip()
        snap = str(raw.get("snap", "") or "").strip()
        snap_index = int(raw.get("snap_index", -1))

        if not anchor_id or anchor_id in seen_ids:
            raise RuntimeError("Ancre : identifiant absent ou dupliqué.")
        if not label:
            raise RuntimeError("Ancre : libellé vide.")

        if snap == "beat":
            if not (0 <= snap_index < len(beats)):
                raise RuntimeError("Ancre : beat hors plage.")
            time_value = float(beats[snap_index]["start"])
        elif snap == "word_boundary":
            if not (1 <= snap_index < len(lead_words)):
                raise RuntimeError("Ancre : frontière de mots hors plage.")
            time_value = (
                float(lead_words[snap_index - 1]["end"])
                + float(lead_words[snap_index]["start"])
            ) / 2.0
        else:
            raise RuntimeError("Ancre : type de snap invalide.")

        seen_ids.add(anchor_id)
        anchors.append(
            {
                "id": anchor_id,
                "label": label,
                "time": time_value,
                "snap": snap,
                "snap_index": snap_index,
            }
        )

    anchors.sort(key=lambda item: (float(item["time"]), item["id"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "source_fingerprint": expected,
        "lead_overrides": lead_overrides,
        "backing_overrides": backing_overrides,
        "line_break_after_lead": line_breaks,
        "chord_overrides": chord_overrides,
        "anchors": anchors,
        "updated_at": str(payload.get("updated_at", "") or ""),
    }


def load(work_dir: Path, lead_words, backing_words, beats) -> dict[str, Any]:
    path = path_for(work_dir)
    if not path.is_file():
        return empty_payload(lead_words, backing_words, beats)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Impossible de lire {path.name}: {exc}") from exc

    expected = fingerprint(lead_words, backing_words, beats)
    stored = str(payload.get("source_fingerprint", "") or "")

    if stored != expected:
        legacy = _legacy_r5_10_fingerprint(
            lead_words,
            backing_words,
            beats,
        )
        if legacy is not None and stored == legacy:
            # Deterministic migration of one known adapter defect only.
            # Beat/word indices do not change, so every editorial override stays
            # attached to the same technical item. validate() recomputes anchor
            # time from its existing snap_index using the corrected beat time.
            payload = dict(payload)
            payload["source_fingerprint"] = expected

    return validate(payload, lead_words, backing_words, beats)


def save(
    work_dir: Path,
    payload,
    lead_words,
    backing_words,
    beats,
) -> dict[str, Any]:
    candidate = dict(payload)
    candidate["schema_version"] = SCHEMA_VERSION
    candidate["source_fingerprint"] = fingerprint(
        lead_words,
        backing_words,
        beats,
    )
    candidate["updated_at"] = _now()

    clean = validate(candidate, lead_words, backing_words, beats)
    clean["updated_at"] = candidate["updated_at"]

    path = path_for(work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return clean
