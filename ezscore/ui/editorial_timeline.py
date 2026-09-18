"""Canonical editorial overlay for EZScore.

Technical timelines remain immutable. This module persists only editorial
overlays used later by the final player and printing.
"""

from __future__ import annotations

import hashlib
import json
import re
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


def normalize_beats(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, beat in enumerate(beats or []):
        start = float(
            beat.get("start", beat.get("temps", beat.get("time_start", 0.0)))
            or 0.0
        )
        end = float(
            beat.get("end", beat.get("fin", beat.get("time_end", start)))
            or start
        )
        if end < start:
            raise RuntimeError(f"Timeline beat invalide à l'index {index}.")
        chord = str(
            beat.get("chord", beat.get("accord", beat.get("label", "."))) or "."
        ).strip() or "."
        result.append(
            {
                "index": index,
                "start": start,
                "end": end,
                "chord": chord,
            }
        )
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
        "time_signature_override": "",
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

    time_signature_override = str(
        payload.get("time_signature_override", "") or ""
    ).strip()
    if time_signature_override:
        match = re.fullmatch(
            r"([1-9][0-9]?)/(1|2|4|8|16|32)",
            time_signature_override,
        )
        if not match:
            raise RuntimeError(
                "time_signature_override: signature invalide "
                "(exemples : 2/4, 3/4, 4/4, 6/8)."
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
        "time_signature_override": time_signature_override,
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
