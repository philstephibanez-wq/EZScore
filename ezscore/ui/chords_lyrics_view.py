from __future__ import annotations

"""Read-only Analyse view for chords + lyrics.

This module intentionally does not edit or persist anything.
Technical analysis remains authoritative. Editorial line breaks are reused only
for presentation when their indices are still valid; otherwise a deterministic
read-only reflow prevents the old giant-paragraph regression.
"""

from html import escape
import json
from pathlib import Path
from typing import Any

import streamlit as st


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _normalize_words(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for item in raw or []:
        text = str(item.get("text", "") or "").strip()
        if not text:
            continue
        start = float(item.get("start", 0.0) or 0.0)
        end = float(item.get("end", start) or start)
        words.append({
            "index": len(words),
            "text": text,
            "start": start,
            "end": max(start, end),
        })
    return words


def _load_beats(work_dir: Path) -> list[dict[str, Any]]:
    structure = _load_json(work_dir / "structure_analysis.json")
    timeline = list(structure.get("beat_timeline", []) or [])
    if timeline:
        beats = []
        for i, item in enumerate(timeline):
            start = float(item.get("time", 0.0) or 0.0)
            if i + 1 < len(timeline):
                end = float(timeline[i + 1].get("time", start) or start)
            else:
                end = start + 0.5
            beats.append({
                "start": start,
                "end": max(start, end),
                "chord": str(item.get("chord", ".") or ".").strip() or ".",
            })
        return beats

    conductor = _load_json(work_dir / "karaoke_conductor.json")
    result = []
    for item in list(conductor.get("beats", []) or []):
        start = float(item.get("start", 0.0) or 0.0)
        end = float(item.get("end", start) or start)
        result.append({
            "start": start,
            "end": max(start, end),
            "chord": str(item.get("chord", ".") or ".").strip() or ".",
        })
    return result


def _saved_line_breaks(work_dir: Path, word_count: int) -> set[int]:
    payload = _load_json(work_dir / "editorial_timeline.json")
    raw = payload.get("line_break_after_lead", [])
    result: set[int] = set()
    if isinstance(raw, list):
        for value in raw:
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= index < max(0, word_count - 1):
                result.add(index)
    return result


def _automatic_line_breaks(words: list[dict[str, Any]]) -> set[int]:
    """Deterministic read-only reflow when no saved line layout exists."""
    breaks: set[int] = set()
    line_len = 0
    strong_endings = (".", "!", "?", ";", ":")

    for i, word in enumerate(words[:-1]):
        line_len += 1
        text = str(word["text"])
        gap = float(words[i + 1]["start"]) - float(word["end"])

        should_break = (
            text.endswith(strong_endings)
            or gap >= 1.05
            or line_len >= 10
        )
        if should_break:
            breaks.add(i)
            line_len = 0

    return breaks


def _chord_at(time_value: float, beats: list[dict[str, Any]]) -> str:
    if not beats:
        return ""
    # Binary-search-like forward scan is unnecessary at current song sizes;
    # deterministic linear scan keeps the view simple and read-only.
    current = ""
    for beat in beats:
        if float(beat["start"]) > time_value:
            break
        current = str(beat.get("chord", "") or "")
        if float(beat["start"]) <= time_value < float(beat["end"]):
            return "" if current == "." else current
    return "" if current == "." else current


def _lines(words: list[dict[str, Any]], breaks: set[int]) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for i, word in enumerate(words):
        current.append(word)
        if i in breaks:
            result.append(current)
            current = []
    if current:
        result.append(current)
    return result


def render_chords_lyrics_view(
    *,
    audio_hash: str,
    speech: dict[str, Any],
    work_dir: Path,
) -> None:
    words = _normalize_words(list(speech.get("words", []) or []))
    if not words:
        st.info("Aucun mot horodaté à afficher.")
        return

    beats = _load_beats(Path(work_dir))
    saved = _saved_line_breaks(Path(work_dir), len(words))
    breaks = saved or _automatic_line_breaks(words)

    line_groups = _lines(words, breaks)

    css = """
    <style>
    .ezcl-wrap{
      border:1px solid rgba(160,170,190,.18);
      border-radius:10px;
      padding:14px 16px;
      background:rgba(255,255,255,.018);
    }
    .ezcl-line{
      display:flex;
      flex-wrap:nowrap;
      align-items:flex-end;
      gap:7px;
      min-height:58px;
      margin:1px 0 7px 0;
      overflow-x:auto;
      padding-bottom:3px;
    }
    .ezcl-slot{
      display:inline-flex;
      flex-direction:column;
      align-items:flex-start;
      flex:0 0 auto;
      min-width:max-content;
    }
    .ezcl-chord{
      height:23px;
      color:#62b6ff;
      font-family:Consolas,"Courier New",monospace;
      font-size:16px;
      font-weight:900;
      line-height:20px;
    }
    .ezcl-word{
      color:#f4f4f4;
      font-size:19px;
      font-weight:690;
      line-height:25px;
      white-space:nowrap;
    }
    .ezcl-sep{
      height:1px;
      margin:1px 0 5px;
      background:rgba(160,170,190,.08);
    }
    </style>
    """

    chunks = [css, '<div class="ezcl-wrap">']
    previous_chord = None

    for line_index, line in enumerate(line_groups):
        chunks.append('<div class="ezcl-line">')
        previous_chord = None
        for word in line:
            chord = _chord_at(float(word["start"]), beats)
            shown_chord = chord if chord and chord != previous_chord else ""
            if chord:
                previous_chord = chord

            chunks.append(
                '<span class="ezcl-slot">'
                f'<span class="ezcl-chord">{escape(shown_chord)}</span>'
                f'<span class="ezcl-word">{escape(str(word["text"]))}</span>'
                '</span>'
            )
        chunks.append("</div>")
        if line_index + 1 < len(line_groups):
            chunks.append('<div class="ezcl-sep"></div>')

    chunks.append("</div>")

    st.markdown("".join(chunks), unsafe_allow_html=True)

    source = (
        "sauts de ligne éditoriaux existants"
        if saved
        else "reflow automatique de lecture"
    )
    st.caption(
        f"Vue Analyse en lecture seule · accords techniques + paroles · {source}. "
        "Aucune donnée technique ou éditoriale n'est modifiée."
    )
